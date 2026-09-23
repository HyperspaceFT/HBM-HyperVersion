package com.hbm.blockentity.machine;

import com.hbm.blockentity.machine.heater.HeaterFireboxBlockEntity;
import com.hbm.inventory.menus.MachinePressMenu;
import com.hbm.inventory.recipes.PressRecipes;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.StampItem;
import com.hbm.items.machine.StampItem.StampType;
import com.hbm.inventory.fluid.Fluids;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

public class Goal5BProcessingRegression {
    private static int checks;
    private static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
    private static MachinePressBlockEntity press(Level level,int x){var m=new MachinePressBlockEntity(new BlockPos(x,1,0),new BlockState());level.put(m);return m;}
    private static void ticks(MachinePressBlockEntity machine,int n){for(int i=0;i<n;i++)machine.updateEntity();}
    private static ItemStack stamp(StampType type,int durability){return new ItemStack(new StampItem("stamp_"+type,type,durability));}
    private static MachinePressBlockEntity ready(StampType type,ItemStack input){var m=press(new Level(),10);m.slots.set(0,new ItemStack(Items.COAL));m.slots.set(1,stamp(type,32));m.slots.set(2,input);m.burnTime=200;return m;}
    private static void coldChain(){
        new PressRecipes().registerDefaults();
        var level=new Level();
        var fire=new HeaterFireboxBlockEntity(new BlockPos(0,0,0),new BlockState());level.put(fire);
        var oven=new MachineFurnaceCombinationBlockEntity(new BlockPos(0,1,0),new BlockState());level.put(oven);
        fire.slots.set(0,new ItemStack(Items.COAL,2));
        oven.slots.set(0,new ItemStack(Items.COAL));
        int ticks=0;
        while(oven.slots.get(1).isEmpty()&&ticks++<4500){fire.updateEntity();oven.updateEntity();}
        check(oven.slots.get(1).is(NtmItems.COKE_COAL.get())&&oven.slots.get(1).getCount()==1
                &&oven.slots.get(0).isEmpty()&&oven.tank.getFill()==100
                &&oven.tank.getTankType()==Fluids.COALCREOSOTE,
                "cold coal-fired oven makes one coal coke and 100 creosote");
        ItemStack sameCoke=oven.slots.get(1);oven.slots.set(1,ItemStack.EMPTY);
        var machine=press(level,4);
        machine.slots.set(0,new ItemStack(Items.COAL,2));
        machine.slots.set(1,stamp(StampType.FLAT,32));
        machine.slots.set(2,sameCoke);
        int cycles=0;
        while(machine.slots.get(3).isEmpty()&&cycles++<4500)machine.updateEntity();
        check(machine.slots.get(3).is(NtmItems.INGOT_GRAPHITE.get())
                &&machine.slots.get(3).getCount()==1&&sameCoke.isEmpty(),
                "same produced coke stack enters live FLAT press and becomes graphite");
        ItemStack flatStamp=machine.slots.get(1);
        check(flatStamp.getDamageValue()==1&&machine.burnTime==1400,
                "first press completion spends 200 of coal's 1600 burn points and wears FLAT stamp once");
        check(fire.burnTime>0&&machine.burnTime>0&&machine.burnTime<1600,
                "firebox TU burn ticks and press operation burn points are separate states");
        ItemStack graphite=machine.slots.get(3);machine.slots.set(3,ItemStack.EMPTY);
        machine.slots.set(1,stamp(StampType.WIRE,64));
        machine.slots.set(2,graphite);
        int wireTicks=0;
        while(machine.slots.get(3).isEmpty()&&wireTicks++<4500)machine.updateEntity();
        check(machine.slots.get(3).is(NtmItems.WIRE_CARBON.get())
                &&machine.slots.get(3).getCount()==8&&graphite.isEmpty(),
                "same graphite stack enters live WIRE press and makes eight carbon wires");
        check(machine.burnTime==1200&&machine.slots.get(1).getDamageValue()==1
                &&flatStamp.getDamageValue()==1&&machine.slots.get(0).getCount()==1,
                "two press operations spend exactly 400 burn points and one wear on each stamp");
        check(machine.slots.get(2).isEmpty()&&oven.tank.getFill()==100,
                "one oven input and two press operations consume exactly their own inputs");
        ticks(machine,30);
        check(machine.slots.get(3).getCount()==8,"returning press cannot duplicate carbon wire after input is spent");
    }
    private static void recipeAndOutputGates(){
        new PressRecipes().registerDefaults();
        var flat=stamp(StampType.FLAT,32);var wire=stamp(StampType.WIRE,64);
        for(Item coke:new Item[]{NtmItems.COKE_COAL.get(),NtmItems.COKE_LIGNITE.get(),NtmItems.COKE_PETROLEUM.get()}){
            check(PressRecipes.getOutput(new ItemStack(coke),flat).is(NtmItems.INGOT_GRAPHITE.get())
                    &&PressRecipes.getInputCount(new ItemStack(coke),flat)==1,
                    "all three coke identities have FLAT one-to-one graphite recipes");
            check(PressRecipes.getOutput(new ItemStack(coke),wire).isEmpty(),
                    "wrong WIRE stamp cannot flatten coke");
        }
        check(PressRecipes.getOutput(new ItemStack(NtmItems.INGOT_GRAPHITE.get()),wire).is(NtmItems.WIRE_CARBON.get())
                &&PressRecipes.getOutput(new ItemStack(NtmItems.INGOT_GRAPHITE.get()),wire).getCount()==8,
                "graphite WIRE recipe yields eight carbon wires");
        check(PressRecipes.getOutput(new ItemStack(new Item("hbmsntm:block_coke")),flat).isEmpty()
                &&PressRecipes.getOutput(new ItemStack(new Item("hbmsntm:block_graphite")),wire).isEmpty(),
                "coke and graphite lookalike blocks are not item recipes");
        var insufficient=ready(StampType.FLAT,new ItemStack(NtmItems.COKE_COAL.get()));
        insufficient.burnTime=199;insufficient.slots.set(0,ItemStack.EMPTY);
        check(!insufficient.canProcess(),"press needs at least 200 stored burn points");
        insufficient.burnTime=200;insufficient.slots.set(1,ItemStack.EMPTY);
        check(!insufficient.canProcess(),"press needs a stamp");
        insufficient.slots.set(1,wire);
        check(!insufficient.canProcess(),"wrong stamp blocks processing");
        var custom=new Item("custom_coke");var customOutput=new Item("custom_graphite");
        PressRecipes.makeRecipe(StampType.FLAT,new ComparableStack(custom,3),new ItemStack(customOutput,2));
        check(PressRecipes.getOutput(new ItemStack(custom,2),flat).isEmpty()
                &&PressRecipes.getOutput(new ItemStack(custom,3),flat).getCount()==2
                &&PressRecipes.getInputCount(new ItemStack(custom,3),flat)==3,
                "custom multi-count recipe rejects two and accepts exactly three");
        var customMachine=ready(StampType.FLAT,new ItemStack(custom,4));
        customMachine.slots.set(0,ItemStack.EMPTY);customMachine.burnTime=200;
        customMachine.speed=400;customMachine.press=199;
        customMachine.updateEntity();
        check(customMachine.slots.get(3).is(customOutput)&&customMachine.slots.get(3).getCount()==2
                &&customMachine.slots.get(2).getCount()==1&&customMachine.burnTime==0,
                "live press consumes exactly three of four custom inputs for two outputs");
        var output=ready(StampType.WIRE,new ItemStack(NtmItems.INGOT_GRAPHITE.get()));
        output.slots.set(3,new ItemStack(NtmItems.WIRE_CARBON.get(),56));
        check(output.canProcess(),"56 carbon wires plus eight exactly fits 64");
        output.slots.set(3,new ItemStack(NtmItems.WIRE_CARBON.get(),57));
        check(!output.canProcess(),"57 carbon wires blocks output of eight");
        output.slots.set(3,new ItemStack(NtmItems.WIRE_CARBON.get(),64));
        check(!output.canProcess()&&output.slots.get(2).getCount()==1,"full output blocks without input consumption");
        var exact=ready(StampType.WIRE,new ItemStack(NtmItems.INGOT_GRAPHITE.get()));
        exact.slots.set(0,ItemStack.EMPTY);exact.slots.set(1,stamp(StampType.WIRE,1));
        exact.slots.set(3,new ItemStack(NtmItems.WIRE_CARBON.get(),56));
        exact.speed=400;exact.press=199;exact.updateEntity();
        check(exact.slots.get(3).getCount()==64&&exact.slots.get(2).isEmpty()
                &&exact.slots.get(1).isEmpty()&&exact.burnTime==0,
                "exact 56+8 completion reaches 64, consumes one input and last stamp use plus 200 burn");
        var blocked=ready(StampType.WIRE,new ItemStack(NtmItems.INGOT_GRAPHITE.get()));
        blocked.slots.set(0,ItemStack.EMPTY);blocked.slots.set(1,stamp(StampType.WIRE,1));
        blocked.slots.set(3,new ItemStack(NtmItems.WIRE_CARBON.get(),57));
        blocked.speed=400;blocked.press=199;ticks(blocked,20);
        check(blocked.slots.get(3).getCount()==57&&blocked.slots.get(2).getCount()==1
                &&blocked.slots.get(1).getDamageValue()==0&&blocked.burnTime==200,
                "57+8 blocked over a cycle leaves output, input, last stamp use and fuel untouched");
        output.slots.set(3,new ItemStack(NtmItems.WIRE_CARBON.get(),1).component("different"));
        check(!output.canProcess(),"output component mismatch blocks press");
        var smallLevel=new Level();
        var small=new MachinePressBlockEntity(new BlockPos(20,1,0),new BlockState()){
            @Override public int getMaxStackSize(){return 1;}
        };
        smallLevel.put(small);small.burnTime=200;
        small.slots.set(1,wire);small.slots.set(2,new ItemStack(NtmItems.INGOT_GRAPHITE.get()));
        check(!small.canProcess(),"empty output respects smaller container maximum");
    }
    private static void stampAndPersistence(){
        new PressRecipes().registerDefaults();
        for(int durability:new int[]{32,64}){
            var m=ready(durability==32?StampType.FLAT:StampType.WIRE,
                    new ItemStack(durability==32?NtmItems.COKE_COAL.get():NtmItems.INGOT_GRAPHITE.get()));
            m.slots.set(0,ItemStack.EMPTY);
            m.slots.set(1,stamp(durability==32?StampType.FLAT:StampType.WIRE,durability));
            m.slots.get(1).setDamageValue(durability-1);
            m.speed=400;m.press=199;m.updateEntity();
            check(m.slots.get(1).isEmpty()&&!m.slots.get(3).isEmpty()&&m.burnTime==0,
                    "last valid stamp use at durability "+durability+" completes then breaks");
            ticks(m,20);
            check(m.slots.get(3).getCount()==(durability==32?1:8),
                    "broken stamp cannot duplicate completed output");
        }
        var infinite=ready(StampType.FLAT,new ItemStack(NtmItems.COKE_COAL.get()));
        infinite.slots.set(0,ItemStack.EMPTY);infinite.slots.set(1,stamp(StampType.FLAT,0));
        infinite.speed=400;infinite.press=199;infinite.updateEntity();
        check(!infinite.slots.get(1).isEmpty()&&infinite.slots.get(1).getDamageValue()==0
                &&infinite.slots.get(3).is(NtmItems.INGOT_GRAPHITE.get()),
                "zero-durability Desh-like stamp survives successful production");
        var m=ready(StampType.FLAT,new ItemStack(NtmItems.COKE_COAL.get()));
        ticks(m,80);
        check(m.slots.get(3).isEmpty()&&m.slots.get(2).getCount()==1,
                "partial press cycle has not consumed input");
        var saved=new CompoundTag();m.saveAdditional(saved,null);
        var resumed=press(new Level(),25);resumed.loadAdditional(saved,null);
        check(resumed.speed==m.speed&&resumed.press==m.press&&resumed.burnTime==m.burnTime
                &&resumed.slots.get(2).is(NtmItems.COKE_COAL.get()),
                "press save/load resumes partial cycle with input and fuel");
        int n=0;while(resumed.slots.get(3).isEmpty()&&n++<4500)resumed.updateEntity();
        check(resumed.slots.get(3).is(NtmItems.INGOT_GRAPHITE.get())
                &&resumed.slots.get(3).getCount()==1&&resumed.slots.get(2).isEmpty(),
                "resumed partial cycle finishes exactly one graphite");
        ticks(resumed,50);
        check(resumed.slots.get(3).getCount()==1,"post-resume cycle cannot duplicate graphite");

        var interrupted=ready(StampType.FLAT,new ItemStack(NtmItems.COKE_COAL.get()));
        ticks(interrupted,80);
        check(interrupted.press>0&&interrupted.slots.get(3).isEmpty(),
                "press has partially extended before interruption");
        interrupted.slots.set(1,ItemStack.EMPTY);
        ticks(interrupted,80);
        check(interrupted.slots.get(2).getCount()==1&&interrupted.slots.get(3).isEmpty()
                &&interrupted.press==0,"missing stamp retracts without consuming coke or producing graphite");
        interrupted.slots.set(1,stamp(StampType.FLAT,32));
        int attempts=0;
        while(interrupted.slots.get(3).isEmpty()&&attempts++<4500)interrupted.updateEntity();
        check(interrupted.slots.get(3).is(NtmItems.INGOT_GRAPHITE.get())
                &&interrupted.slots.get(3).getCount()==1&&interrupted.slots.get(2).isEmpty(),
                "restored stamp restarts and completes exactly one graphite");

        var starved=ready(StampType.FLAT,new ItemStack(NtmItems.COKE_COAL.get()));
        starved.slots.set(0,ItemStack.EMPTY);starved.speed=400;starved.press=100;
        starved.updateEntity();
        check(starved.press>100&&starved.slots.get(3).isEmpty(),
                "preloaded burn drives a partial press stroke without a fuel item");
        starved.burnTime=0;ticks(starved,20);
        check(starved.press==0&&starved.slots.get(2).getCount()==1
                &&starved.slots.get(3).isEmpty()&&starved.slots.get(1).getDamageValue()==0,
                "stored fuel exhaustion retracts without free output, input or stamp wear");
    }
    private static void quickMoveCoke(){
        var level=new Level();var m=press(level,30);
        var player=new Player();player.world=level;var inv=player.getInventory();inv.player=player;
        var menu=new MachinePressMenu(0,inv,m);
        inv.setItem(0,new ItemStack(NtmItems.COKE_COAL.get()));
        check(!menu.quickMoveStack(player,menu.slots.size()-9).isEmpty()
                &&m.slots.get(0).is(NtmItems.COKE_COAL.get())&&m.slots.get(2).isEmpty(),
                "current Shift routing sends burnable coke to press fuel slot");
    }
    public static void main(String[] args){
        coldChain();System.out.println("cold coal-to-wire chain: passed");
        recipeAndOutputGates();System.out.println("recipe and output gates: passed");
        stampAndPersistence();System.out.println("stamp and persistence: passed");
        quickMoveCoke();System.out.println("current quick-move routing: passed");
        System.out.println("Goal 5B processing checks: "+checks);
    }
}
