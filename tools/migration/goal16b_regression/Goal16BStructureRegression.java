package goal16b;

import java.util.*;

/** Placement/teardown bodies are production; world replacement and inventory drops are services. */
public class Goal16BStructureRegression {
    static int checks, scenarios;
    static final BlockPos CORE = new BlockPos(0,64,0);
    static void check(boolean v,String m){checks++;if(!v)throw new AssertionError(m);}
    static Set<BlockPos> cells(BlockPos core){return Set.of(core,core.above(),core.above(2),core.above(3));}
    static Set<BlockPos> occupied(Level l,Block b){Set<BlockPos> s=new HashSet<>();for(var e:l.states.entrySet())if(e.getValue().getBlock()==b)s.add(e.getKey());return s;}
    static void place(Centrifuge b,Level l,BlockPos core,Direction d){BlockState s=b.defaultBlockState().setValue(DummyableBlock.FACING,d);l.states.put(core,s);Player p=new Player();ItemStack item=new ItemStack(4);b.setPlacedBy(l,core,s,p,item);item.consume(p);check(item.count==3,"one item consumed");}
    public static void main(String[] args){
        for(Direction d:new Direction[]{Direction.NORTH,Direction.SOUTH,Direction.EAST,Direction.WEST}){
            scenarios++;Centrifuge b=new Centrifuge();Level l=new Level();place(b,l,CORE,d);check(occupied(l,b).equals(cells(CORE)),"exact vertical four cells "+d);
            for(BlockPos p:cells(CORE)){check(CORE.equals(b.findCore(l,p)),"all links resolve core "+p);BlockEntity be=b.newBlockEntity(p,l.getBlockState(p));if(p.equals(CORE))check(be instanceof MachineCentrifugeBlockEntity,"core entity");else check(be==null,"non-core remains dummy");}
            for(BlockPos obstruction:List.of(CORE.above(),CORE.above(2),CORE.above(3))){scenarios++;l=new Level();Block foreign=new Block();l.states.put(obstruction,foreign.defaultBlockState());BlockState s=b.defaultBlockState().setValue(DummyableBlock.FACING,d);l.states.put(CORE,s);Player p=new Player();ItemStack stack=new ItemStack(64);stack.components.put("custom","keep");b.setPlacedBy(l,CORE,s,p,stack);stack.consume(p);check(stack.count==64&&stack.components.equals(Map.of("custom","keep")),"blocked placement refund preserves components");check(occupied(l,b).isEmpty()&&l.getBlockState(obstruction).getBlock()==foreign,"no partial structure");}
            for(BlockPos removed:cells(CORE))for(boolean playerBreak:new boolean[]{false,true})for(boolean stacked:new boolean[]{false,true}){
                scenarios++;l=new Level();place(b,l,CORE,d);BlockPos neighbor=stacked?CORE.above(4):CORE.relative(d);place(b,l,neighbor,d);l.inventoryDrops=0;l.drops=0;BlockState old=l.getBlockState(removed);if(playerBreak)b.playerWillDestroy(l,removed,old,new Player());l.removeBlock(removed,false);check(occupied(l,b).equals(cells(neighbor)),"owned teardown preserves touching/stacked neighbor "+removed+"/"+d);check(l.inventoryDrops==1,"core inventory engine drop exactly once");check(l.drops==(playerBreak?1:0),"player core machine drop once; replacement no extra item drop");check(!DummyableBlock.safeRem,"guard restored");
            }
            for(BlockPos replaced:cells(CORE)){
                scenarios++;l=new Level();place(b,l,CORE,d);BlockPos neighbor=CORE.above(4);place(b,l,neighbor,d);Block foreign=new Block();l.inventoryDrops=0;l.setBlock(replaced,foreign.defaultBlockState(),3);check(occupied(l,b).equals(cells(neighbor)),"replacement only destroys owned centrifuge");check(l.getBlockState(replaced).getBlock()==foreign,"foreign replacement retained "+replaced);check(l.inventoryDrops==1,"replacement inventory dropped once");
            }
        }
        System.out.println("Goal16B structural methods: "+checks+" checks; "+scenarios+" independent scenarios; engine inventory drop model, no real loot proof");
    }
}
