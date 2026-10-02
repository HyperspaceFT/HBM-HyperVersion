package com.hbm.blockentity.machine;

import com.hbm.blockentity.machine.heater.HeaterFireboxBlockEntity;
import com.hbm.inventory.material.MaterialShapes;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.recipes.CopperCastingRecipes;
import com.hbm.items.CopperScrapsItem;
import com.hbm.items.NtmItems;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import com.hbm.inventory.menus.MachineCrucibleMenu;
import com.hbm.inventory.material.NTMMaterial;

import java.lang.reflect.Method;

public class CastingRegression {
    private static int checks;
    private static void check(boolean ok, String message) { checks++; if(!ok) throw new AssertionError(message); }
    private static HeaterFireboxBlockEntity fire(Level l,BlockPos p) {
        var be=new HeaterFireboxBlockEntity(p,new BlockState());l.put(be);return be;
    }
    private static MachineCrucibleBlockEntity crucible(Level l,BlockPos p) {
        var be=new MachineCrucibleBlockEntity(p,new BlockState());l.put(be);return be;
    }
    private static FoundryMoldBlockEntity mold(Level l,BlockPos p) {
        var be=new FoundryMoldBlockEntity(p,new BlockState());l.put(be);return be;
    }
    private static void save(Object be,CompoundTag tag) {
        try {Method m=be.getClass().getDeclaredMethod("saveAdditional",CompoundTag.class,net.minecraft.core.HolderLookup.Provider.class);m.setAccessible(true);m.invoke(be,tag,null);}
        catch(ReflectiveOperationException ex){throw new AssertionError(ex);}
    }
    private static void load(Object be,CompoundTag tag) {
        try {Method m=be.getClass().getDeclaredMethod("loadAdditional",CompoundTag.class,net.minecraft.core.HolderLookup.Provider.class);m.setAccessible(true);m.invoke(be,tag,null);}
        catch(ReflectiveOperationException ex){throw new AssertionError(ex);}
    }
    // Goal 10A replaced the single copper amount with a recipe stack and a waste stack. Without a selected recipe all
    // copper is unalloyed and lives in the waste stack, which pours from the rear spout like the Goal 5A buffer did.
    private static int copper(MachineCrucibleBlockEntity be) {
        return MachineCrucibleBlockEntity.getQuantaFromType(be.wasteStack,Mats.MAT_COPPER);
    }
    private static void setCopper(MachineCrucibleBlockEntity be,int n) {
        be.wasteStack.clear();if(n>0)be.wasteStack.add(new Mats.MaterialStack(Mats.MAT_COPPER,n));
    }
    /** The Goal 5A CopperScrapsItem.getAmount contract: copper quanta of a valid scrap, otherwise 0. */
    private static int scrapAmount(ItemStack s) {
        var m=CopperScrapsItem.getMats(s);return m==null||m.material!=Mats.MAT_COPPER?0:m.amount;
    }
    private static int inputs(MachineCrucibleBlockEntity be) {
        int n=0;for(ItemStack s:be.slots)n+=s.getCount();return n;
    }
    private static void coldTwoPlates() {
        var level=new Level();
        var source=fire(level,new BlockPos(0,0,0));
        var crucible=crucible(level,new BlockPos(0,1,0));
        var mold=mold(level,new BlockPos(0,0,2));
        source.slots.set(0,new ItemStack(Items.COAL,2));
        for(int i=0;i<6;i++)crucible.slots.set(i,new ItemStack(Items.COPPER_INGOT));
        var moldInput=new ItemStack(NtmItems.MOLD_PLATE_CAST.get());
        check(mold.insertMold(moldInput) && moldInput.isEmpty(),"reusable plate mold inserted once");
        level.nextHit=new BlockHitResult(HitResult.Type.BLOCK,mold.getBlockPos(),Direction.UP);
        int collected=0,firstAt=-1;
        for(int tick=0;tick<4500 && collected<2;tick++) {
            source.updateEntity();
            crucible.updateEntity();
            mold.updateEntity();
            check(inputs(crucible)*72+copper(crucible)+mold.amount+collected*216
                    +(mold.slots.get(1).isEmpty()?0:216)==432,"copper mass conserved through melt/pour/cool");
            if(!mold.slots.get(1).isEmpty()) {
                check(mold.slots.get(1).is(NtmItems.CAST_PLATE.get())
                        && mold.slots.get(1).component().equals("5")
                        && mold.slots.get(1).getCount()==1,"finished item is existing copper castplate META 5");
                if(firstAt<0)firstAt=tick;
                check(mold.slots.get(0).is(NtmItems.MOLD_PLATE_CAST.get()),"mold remains reusable");
                check(!mold.removeItem(1,1).isEmpty(),"extract one completed plate");
                collected++;
            }
        }
        check(collected==2 && inputs(crucible)==0 && copper(crucible)==0 && mold.amount==0,
                "six ingots from cold complete exactly two plates with no residual copper");
        check(firstAt>=200,"first cast includes full cooling time");
        check(level.lastClip!=null
                && level.lastClip.block==net.minecraft.world.level.ClipContext.Block.COLLIDER
                && level.lastClip.fluid==net.minecraft.world.level.ClipContext.Fluid.ANY
                && level.lastClip.collision instanceof net.minecraft.world.phys.shapes.CollisionContext,
                "pour invokes collider/any downward ray with explicit collision context");
        check(Math.abs(level.lastClip.start.x()-0.5)<1e-9
                && Math.abs(level.lastClip.start.z()-2.375)<1e-9
                && Math.abs(level.lastClip.start.y()-1.25)<1e-9
                && Math.abs(level.lastClip.end.y()+4.75)<1e-9,
                "rear source-shaped spout ray starts 1.875 out and reaches six down");
    }
    private static void heatAndRefusal() {
        var level=new Level();
        var c=crucible(level,new BlockPos(10,1,0));
        var f=fire(level,new BlockPos(10,0,0));
        f.heatEnergy=100_000;
        c.updateEntity();
        check(c.heat==25_000&&f.heatEnergy==75_000,"crucible diffuses ceil(min(source diff, room)*.25)");
        c.heat=99_999;f.heatEnergy=100_000;c.updateEntity();
        check(c.heat==100_000&&f.heatEnergy==99_999,"one positive difference rounds up");
        c.heat=99_000;f.heatEnergy=150_000;c.updateEntity();
        check(c.heat==99_250&&f.heatEnergy==149_750,
                "crucible caps source difference to available room before quarter diffusion");
        c.heat=100_000;f.heatEnergy=150_000;c.updateEntity();
        check(c.heat==100_000&&f.heatEnergy==150_000,"full crucible pauses transfer and cooling");
        c.heat=500;f.heatEnergy=500;c.updateEntity();
        check(c.heat==500,"equal source heat does not cool");
        f.heatEnergy=100;c.updateEntity();check(c.heat==499,"cooler source cools by at least one");
        level.entities.remove(f.getBlockPos());c.heat=5_000;c.updateEntity();
        check(c.heat==4_995,"absent source cools heat/1000");

        c.heat=50_000;c.progress=700;c.updateEntity();
        check(c.progress==0,"no input resets melt progress");
        c.slots.set(0,new ItemStack(Items.COPPER_INGOT));
        c.heat=49_999;f.heatEnergy=49_999;c.progress=700;c.updateEntity();
        check(c.progress==0&&c.slots.get(0).getCount()==1,"below 50000 heat resets pending melt");
        level.put(f);c.heat=50_001;f.heatEnergy=50_001;c.updateEntity();
        check(c.progress==0&&c.slots.get(0).getCount()==1,"floor melt speed zero just above threshold");
        c.heat=50_020;f.heatEnergy=50_020;c.updateEntity();
        check(c.progress==1&&c.heat==50_019,"melt speed floor((heat-50000)*.05) spends equal heat");
        setCopper(c,MachineCrucibleBlockEntity.CAPACITY);c.progress=800;c.updateEntity();
        check(c.progress==0&&c.slots.get(0).getCount()==1,"full copper buffer blocks and resets progress");
        setCopper(c,MachineCrucibleBlockEntity.CAPACITY-71);c.progress=800;c.updateEntity();
        check(c.progress==0&&c.slots.get(0).getCount()==1,"one quantum short of ingot room blocks without consumption");
        check(MachineCrucibleBlockEntity.CAPACITY==10_368,"copper buffer capacity is sixteen blocks");
        var threshold=crucible(level,new BlockPos(11,1,0));
        threshold.slots.set(0,new ItemStack(Items.COPPER_INGOT));
        threshold.heat=100_000;threshold.progress=19_999;threshold.updateEntity();
        check(threshold.slots.get(0).isEmpty()&&copper(threshold)==72&&threshold.progress==0,
                "completed melt consumes one item and discards progress overflow");

        var m=mold(level,new BlockPos(10,0,2));
        var offered=new Mats.MaterialStack(Mats.MAT_COPPER,24);
        check(m.pour(offered)==0&&offered.amount==24,"no plate mold refuses without mutating offered stack");
        m.insertMold(new ItemStack(NtmItems.MOLD_PLATE_CAST.get()));
        check(m.pour(new Mats.MaterialStack(new NTMMaterial(),24))==0,"foreign material refused");
        check(m.pour(new Mats.MaterialStack(Mats.MAT_COPPER,24))==24&&m.amount==24,
                "plate mold accepts up to offered copper");
        check(m.takeMold().isEmpty(),"partly filled mold cannot be removed");
        check(m.pour(new Mats.MaterialStack(Mats.MAT_COPPER,1000))==192&&m.amount==216,
                "mold fills exactly 216 quanta");
        check(m.pour(new Mats.MaterialStack(Mats.MAT_COPPER,1))==0,"full mold refuses overflow");
        for(int i=0;i<199;i++)m.updateEntity();
        check(m.slots.get(1).isEmpty()&&m.cooloff==1,"no output before 200 cooling ticks");
        m.updateEntity();
        check(m.slots.get(1).is(NtmItems.CAST_PLATE.get())&&m.amount==0&&m.cooloff==200,
                "200th cooling tick creates plate and resets mold");
        check(m.pour(new Mats.MaterialStack(Mats.MAT_COPPER,24))==0,"occupied output refuses further pour");
        check(!m.removeItem(1,1).isEmpty()&&m.pour(new Mats.MaterialStack(Mats.MAT_COPPER,24))==24,
                "output extraction reopens reusable mold");
    }
    private static void rayAndIntake() {
        var level=new Level();
        var c=crucible(level,new BlockPos(20,1,0));
        var m=mold(level,new BlockPos(20,0,2));
        setCopper(c,100);
        c.updateEntity();
        check(copper(c)==100,"missing ray hit retains molten copper");
        level.nextHit=new BlockHitResult(HitResult.Type.BLOCK,m.getBlockPos(),Direction.DOWN);
        c.updateEntity();
        check(copper(c)==100,"non-top hit retains molten copper");
        level.nextHit=new BlockHitResult(HitResult.Type.BLOCK,new BlockPos(20,0,9),Direction.UP);
        c.updateEntity();
        check(copper(c)==100,"top hit without receiving mold retains copper");
        level.nextHit=new BlockHitResult(HitResult.Type.BLOCK,m.getBlockPos(),Direction.UP);
        c.updateEntity();
        check(copper(c)==100,"mold without plate insert retains copper");
        m.insertMold(new ItemStack(NtmItems.MOLD_PLATE_CAST.get()));
        c.updateEntity();
        check(copper(c)==76&&m.amount==24,"one live pour offers at most 24 quanta");
        m.amount=216;c.updateEntity();
        check(copper(c)==76,"full target leaves molten copper in source");
        m.amount=0;m.slots.set(1,new ItemStack(NtmItems.CAST_PLATE.get()));
        c.updateEntity();
        check(copper(c)==76,"occupied mold output leaves molten copper in source");

        var intakeLevel=new Level();
        var intake=crucible(intakeLevel,new BlockPos(30,1,0));
        var ingots=new ItemEntity(new ItemStack(Items.COPPER_INGOT,3));
        var invalid=new ItemEntity(new ItemStack(Items.STICK,2));
        intakeLevel.dropped.add(ingots);intakeLevel.dropped.add(invalid);
        intake.updateEntity();
        check(inputs(intake)==3&&ingots.getItem().isEmpty()&&!ingots.isAlive()
                &&invalid.getItem().getCount()==2&&invalid.isAlive(),
                "five-tick intake captures valid drops one item per slot and rejects invalid drop");
        check(intakeLevel.lastIntake!=null&&intakeLevel.lastIntake.a()==29.5
                &&intakeLevel.lastIntake.b()==1.5&&intakeLevel.lastIntake.c()==-0.5
                &&intakeLevel.lastIntake.d()==31.5&&intakeLevel.lastIntake.e()==2.0,
                "intake requests original 2x0.5x2 source-shaped area");
        var later=new ItemEntity(new ItemStack(Items.COPPER_INGOT));
        intakeLevel.dropped.add(later);
        for(int tick=0;tick<4;tick++)intake.updateEntity();
        check(inputs(intake)==3&&later.isAlive(),"intake does not collect during four intervening ticks");
        intake.updateEntity();
        check(inputs(intake)==4&&!later.isAlive(),"next fifth tick collects new valid item");
    }
    private static void saveScrapAndMenu() {
        var level=new Level();
        var c=crucible(level,new BlockPos(40,1,0));
        c.heat=70_000;c.progress=1_250;setCopper(c,37);
        c.slots.set(0,new ItemStack(Items.COPPER_INGOT));
        var saved=new CompoundTag();save(c,saved);
        check(saved.getIntArray("was").length==2&&!saved.contains("copper"),
                "Goal 10A saves unalloyed copper in the waste stack (was) and no longer writes copper");
        var restored=crucible(new Level(),new BlockPos(40,1,0));load(restored,saved);
        check(restored.heat==70_000&&restored.progress==1_250&&copper(restored)==37
                &&restored.slots.get(0).is(Items.COPPER_INGOT),"mid-melt save/load preserves heat, work, copper and input");
        restored.heat=100_000;
        for(int tick=0;tick<30&&!restored.slots.get(0).isEmpty();tick++)restored.updateEntity();
        check(restored.slots.get(0).isEmpty()&&copper(restored)==109&&restored.progress==0,
                "restored partial melt finishes one ingot and preserves prior 37 quanta");
        for(int tick=0;tick<10;tick++)restored.updateEntity();
        check(copper(restored)==109,"post-melt ticks do not duplicate copper");
        var buf=new RegistryFriendlyByteBuf();c.serialize(buf);
        var synced=crucible(new Level(),new BlockPos(40,1,0));synced.deserialize(buf);
        check(synced.heat==70_000&&synced.progress==1_250&&copper(synced)==37,
                "crucible network sync carries heat, progress and copper");
        var bad=new CompoundTag();bad.putInt("heat",Integer.MAX_VALUE);bad.putInt("progress",-1);
        bad.putInt("copper",Integer.MAX_VALUE);load(restored,bad);
        check(restored.heat==100_000&&restored.progress==0&&copper(restored)==10_368,
                "crucible clamps malformed saved values");

        // Goal 10A: the crucible returns one scrap per stored material; copper is its only one here.
        var scraps=c.takeScraps();var scrap=scraps.size()==1?scraps.get(0):ItemStack.EMPTY;
        check(copper(c)==0&&scrapAmount(scrap)==37
                &&scrap.customTag.getInt("material")==2900&&scrap.customTag.getInt("amount")==37,
                "crucible scrap extraction encodes exact copper quanta in custom data");
        var newCrucible=crucible(new Level(),new BlockPos(41,1,0));
        newCrucible.slots.set(0,scrap);
        newCrucible.heat=100_000;
        for(int tick=0;tick<30&&!newCrucible.slots.get(0).isEmpty();tick++)newCrucible.updateEntity();
        check(newCrucible.slots.get(0).isEmpty()&&copper(newCrucible)==37,
                "production scrap recipe remelts without changing copper amount");
        var malformed=CopperScrapsItem.create(new Mats.MaterialStack(Mats.MAT_COPPER,37));
        malformed.customTag.putInt("amount",10_369);
        check(scrapAmount(malformed)==0,"oversize scraps are not accepted as material");
        malformed.customTag.putInt("amount",37);malformed.customTag.putInt("material",999);
        check(scrapAmount(malformed)==0,"foreign scrap material is rejected");

        var mold=mold(level,new BlockPos(40,0,2));
        mold.insertMold(new ItemStack(NtmItems.MOLD_PLATE_CAST.get()));
        mold.pour(new Mats.MaterialStack(Mats.MAT_COPPER,216));
        for(int tick=0;tick<40;tick++)mold.updateEntity();
        var moldTag=new CompoundTag();save(mold,moldTag);
        var resumed=mold(new Level(),new BlockPos(40,0,2));load(resumed,moldTag);
        check(resumed.amount==216&&resumed.cooloff==160&&resumed.hasMold(),
                "mid-cooling save/load preserves molten amount, timer and reusable mold");
        for(int tick=0;tick<159;tick++)resumed.updateEntity();
        check(resumed.slots.get(1).isEmpty()&&resumed.cooloff==1,"resumed cooling has no early output");
        resumed.updateEntity();
        check(resumed.slots.get(1).is(NtmItems.CAST_PLATE.get())&&resumed.amount==0,
                "resumed 200-tick cooling finishes exactly one plate");
        var moldBuf=new RegistryFriendlyByteBuf();mold.serialize(moldBuf);
        var moldSynced=mold(new Level(),new BlockPos(40,0,2));moldSynced.deserialize(moldBuf);
        check(moldSynced.amount==216&&moldSynced.cooloff==160&&moldSynced.hasMold(),
                "mold sync carries material, timer and mold slot");
        var moldClientLevel=new Level();moldClientLevel.isClientSide=true;
        var moldClient=mold(moldClientLevel,new BlockPos(45,0,2));
        moldClient.insertMold(new ItemStack(NtmItems.MOLD_PLATE_CAST.get()));
        moldClient.slots.set(0,new ItemStack(NtmItems.MOLD_PLATE_CAST.get()));
        moldClient.amount=216;moldClient.type=Mats.MAT_COPPER;
        moldClient.updateEntity();
        check(moldClient.cooloff==200&&moldClient.slots.get(1).isEmpty()
                &&moldClient.pour(new Mats.MaterialStack(Mats.MAT_COPPER,1))==0,
                "client mold neither cools nor accepts state-changing pour");

        var partial=mold(new Level(),new BlockPos(42,0,2));
        partial.insertMold(new ItemStack(NtmItems.MOLD_PLATE_CAST.get()));
        partial.pour(new Mats.MaterialStack(Mats.MAT_COPPER,73));
        var moldScrap=partial.takeScraps();
        check(partial.amount==0&&scrapAmount(moldScrap)==73
                &&partial.takeMold().is(NtmItems.MOLD_PLATE_CAST.get()),
                "partial mold can return exact scrap and reusable mold");
        check(partial.getSlotsForFace(Direction.NORTH).length==1
                &&partial.getSlotsForFace(Direction.NORTH)[0]==1
                &&partial.canTakeItemThroughFace(1,ItemStack.EMPTY,Direction.NORTH)
                &&!partial.canTakeItemThroughFace(0,ItemStack.EMPTY,Direction.NORTH)
                &&!partial.canPlaceItem(0,new ItemStack(NtmItems.MOLD_PLATE_CAST.get())),
                "mold automation exposes output only; insertion remains manual");

        var player=new Player();player.world=level;Inventory inv=player.getInventory();inv.player=player;
        var menu=new MachineCrucibleMenu(0,inv,restored);
        check(menu.quickMoveStack(player,-1).isEmpty()&&menu.quickMoveStack(player,menu.slots.size()).isEmpty(),
                "crucible menu rejects invalid quick-move indices");
        check(restored.getMaxStackSize()==1&&restored.getContainerSize()==9
                &&restored.getSlotsForFace(Direction.NORTH).length==9
                &&!restored.canTakeItemThroughFace(0,new ItemStack(Items.COPPER_INGOT),Direction.NORTH),
                "nine one-item input slots expose no automated extraction");
        var empty=crucible(level,new BlockPos(43,1,0));
        var shift=new MachineCrucibleMenu(0,inv,empty);
        inv.setItem(0,new ItemStack(Items.COPPER_INGOT,12));
        check(!shift.quickMoveStack(player,shift.slots.size()-9).isEmpty()
                &&inputs(empty)==9&&inv.getItem(0).getCount()==3,
                "shift-insertion fills exactly nine single-item crucible slots");
        var guarded=crucible(level,new BlockPos(46,1,0));
        guarded.slots.set(0,new ItemStack(Items.COPPER_INGOT));
        check(!guarded.canPlaceItemThroughFace(0,new ItemStack(Items.COPPER_INGOT),Direction.NORTH)
                &&guarded.canPlaceItemThroughFace(1,new ItemStack(Items.COPPER_INGOT),Direction.NORTH),
                "occupied hopper-facing slot rejects same copper while empty next slot accepts");
        var guardedMenu=new MachineCrucibleMenu(0,inv,guarded);
        inv.setItem(2,new ItemStack(Items.COPPER_INGOT,2));
        check(!guardedMenu.quickMoveStack(player,guardedMenu.slots.size()-7).isEmpty()
                &&guarded.slots.get(0).getCount()==1
                &&guarded.slots.get(1).getCount()==1
                &&guarded.slots.get(2).getCount()==1
                &&inputs(guarded)==3&&inv.getItem(2).isEmpty(),
                "shift two copper bypasses occupied slot, fills slots 1 and 2, preserves three-item mass");
        for(int slot=3;slot<9;slot++)guarded.slots.set(slot,new ItemStack(Items.COPPER_INGOT));
        inv.setItem(2,new ItemStack(Items.COPPER_INGOT,2));
        check(guardedMenu.quickMoveStack(player,guardedMenu.slots.size()-7).isEmpty()
                &&inputs(guarded)==9&&guarded.slots.get(0).getCount()==1
                &&inv.getItem(2).getCount()==2,
                "all nine occupied one-item slots refuse remainder without input mutation");
        inv.setItem(1,new ItemStack(Items.STICK));
        check(shift.quickMoveStack(player,shift.slots.size()-8).isEmpty()
                &&!empty.canPlaceItem(0,new ItemStack(Items.STICK)),
                "invalid material rejected by shift route and machine slot");
        var clientLevel=new Level();clientLevel.isClientSide=true;
        var client=crucible(clientLevel,new BlockPos(44,1,0));
        client.heat=80_000;client.progress=400;client.slots.set(0,new ItemStack(Items.COPPER_INGOT));
        client.updateEntity();
        check(client.heat==80_000&&client.progress==400&&copper(client)==0,
                "client crucible tick cannot melt material");
    }
    public static void main(String[] args) {
        check(Mats.MAT_COPPER.id==2900 && MaterialShapes.INGOT.q(1)==72
                && CopperCastingRecipes.PLATE_QUANTA==216 && CopperCastingRecipes.POUR_QUANTA==24,
                "copper quanta and material identity");
        coldTwoPlates();System.out.println("cold two-plate chain: passed");
        heatAndRefusal();System.out.println("heat and refusal: passed");
        rayAndIntake();System.out.println("ray and intake: passed");
        saveScrapAndMenu();System.out.println("persistence, scraps and menu: passed");
        System.out.println("Casting checks: "+checks);
    }
}
