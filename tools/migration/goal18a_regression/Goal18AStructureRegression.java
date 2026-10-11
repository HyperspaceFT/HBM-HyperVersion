package goal18a;
import java.util.*;

/** Extracted production structure/lifecycle methods for the crystallizer; engine inventory/loot is a service. */
public class Goal18AStructureRegression {
    static int checks,scenarios;
    static final BlockPos CORE=new BlockPos(0,64,0);
    static final Direction[] FACINGS={Direction.NORTH,Direction.SOUTH,Direction.WEST,Direction.EAST};
    static void check(boolean v,String s){checks++;if(!v)throw new AssertionError(s);}
    /** Original {5,0,1,1,1,1}: the core, five rows above it, one cell to every horizontal side: 3x6x3 = 54 cells for every facing. */
    static Set<BlockPos> footprint(BlockPos p){
        Set<BlockPos> cells=new HashSet<>();
        for(int x=-1;x<=1;x++)for(int y=0;y<=5;y++)for(int z=-1;z<=1;z++)cells.add(p.offset(x,y,z));
        return cells;
    }
    static Set<BlockPos> occupied(Level l,Block b){Set<BlockPos> s=new HashSet<>();for(var e:l.states.entrySet())if(e.getValue().getBlock()==b)s.add(e.getKey());return s;}
    static void place(Crystallizer b,Level l,BlockPos core,Direction f,Player p,ItemStack stack){
        // Offset 1: setPlacedBy moves the core one cell against the facing from the clicked cell, so the clicked cell is core+facing.
        BlockPos clicked=core.relative(f);BlockState s=b.defaultBlockState().setValue(DummyableBlock.FACING,f);
        l.states.put(clicked,s);b.setPlacedBy(l,clicked,s,p,stack);stack.consume(p);
    }
    public static void main(String[] args){
        for(Direction f:FACINGS){
            scenarios++;var b=new Crystallizer();Level l=new Level();Player p=new Player();ItemStack stack=new ItemStack(64);stack.components.put("custom","keep");
            Set<BlockPos> cells=footprint(CORE);place(b,l,CORE,f,p,stack);
            check(cells.size()==54&&occupied(l,b).equals(cells),"original 3x6x3 box "+f+" "+occupied(l,b));
            check(DummyableBlock.isCore(l.getBlockState(CORE))&&l.getBlockState(CORE).getValue(DummyableBlock.FACING)==f,"core at offset 1 with facing "+f);
            check(stack.count==63&&stack.components.equals(Map.of("custom","keep")),"component preserving placement");
            Set<BlockPos> expected=Set.of(CORE.offset(1,0,1),CORE.offset(1,0,-1),CORE.offset(-1,0,1),CORE.offset(-1,0,-1));
            check(new HashSet<>(Arrays.asList(MachineCrystallizerBlockEntity.getCornerProxies(CORE))).equals(expected),"four bottom corners independent of facing "+f);
            Set<BlockPos> extras=new HashSet<>();
            for(BlockPos cell:cells){
                check(CORE.equals(b.findCore(l,cell)),"owned core reachability "+f+cell);
                BlockState s=l.getBlockState(cell);BlockEntity entity=b.newBlockEntity(cell,s);
                if(s.getValue(DummyableBlock.TYPE)==DummyBlockType.EXTRA){
                    extras.add(cell);var proxy=(ProxyComboBlockEntity)entity;check(proxy.inventory&&proxy.power&&proxy.fluid,"proxy inventory, power and fluid");
                }else check(entity==null||cell.equals(CORE),"no dummy BE");
                if(cell.equals(CORE))check(entity instanceof MachineCrystallizerBlockEntity,"core BE");
            }
            check(extras.equals(expected),"exact four proxies "+f);
            DirPos[] connections=MachineCrystallizerBlockEntity.getConnectionPositions(CORE);
            check(connections.length==8,"eight external connections");
            Set<BlockPos> seen=new HashSet<>();
            for(DirPos c:connections){
                BlockPos external=c.makeCompat();BlockPos corner=external.relative(c.getDir().getOpposite());
                check(!cells.contains(external)&&expected.contains(corner),"each connection is the outward neighbour of a corner proxy "+c.getDir()+external);
                check(seen.add(external),"distinct external neighbours");
            }
            Direction side=MachineCrystallizerBlockEntity.getLadderSide(f);
            check(side==f.getClockWise()&&side!=f&&side!=f.getOpposite(),"ladder side is the clockwise side "+f);
            for(BlockPos obstacle:cells){
                if(obstacle.equals(CORE.relative(f)))continue;
                scenarios++;Level bad=new Level();Block solid=new Block();bad.states.put(obstacle,solid.defaultBlockState());ItemStack refund=new ItemStack(64);refund.components.put("custom","keep");place(b,bad,CORE,f,p,refund);
                check(refund.count==64&&refund.components.equals(Map.of("custom","keep")),"blocked at-limit refund keeps components");
                check(occupied(bad,b).isEmpty()&&bad.getBlockState(obstacle).getBlock()==solid,"blocked no partial structure");
            }
            for(boolean direct:new boolean[]{false,true})for(BlockPos removed:cells){
                scenarios++;l=new Level();place(b,l,CORE,f,p,new ItemStack(4));BlockPos neighbor=CORE.relative(f.getClockWise(),3);place(b,l,neighbor,f,p,new ItemStack(4));
                BlockState old=l.getBlockState(removed);if(!direct)b.playerWillDestroy(l,removed,old,p);l.removeBlock(removed,false);
                check(occupied(l,b).equals(footprint(neighbor)),"teardown preserves independent neighbour "+f+removed);
                check(l.inventoryDrops==1&&!DummyableBlock.safeRem,"inventory once guard restored");
                if(!direct)check(l.drops==1,"survival machine loot once");
            }
            for(BlockPos replaced:List.of(CORE,CORE.offset(1,0,1),CORE.above(5),CORE.offset(-1,3,0))){
                scenarios++;l=new Level();place(b,l,CORE,f,p,new ItemStack(4));BlockPos neighbor=CORE.relative(f.getClockWise(),3);place(b,l,neighbor,f,p,new ItemStack(4));Block replacement=new Block();l.setBlock(replaced,replacement.defaultBlockState(),3);
                check(l.getBlockState(replaced).getBlock()==replacement&&occupied(l,b).equals(footprint(neighbor)),"nonair replacement preserved with neighbour");
                check(l.inventoryDrops==1&&!DummyableBlock.safeRem,"replace inventory once");
            }
            scenarios++;l=new Level();place(b,l,CORE,f,p,new ItemStack(4));BlockPos foreign=CORE.above(6);l.states.put(foreign,b.defaultBlockState().setValue(DummyableBlock.FACING,f));l.removeBlock(CORE,false);
            check(l.getBlockState(foreign).getBlock()==b&&DummyableBlock.isCore(l.getBlockState(foreign)),"foreign core just outside the box preserved");
            // A foreign core (another machine's state) sitting inside the candidate box is not linked to this core and must survive the teardown.
            for(BlockPos inside:List.of(CORE.offset(1,2,1),CORE.above(5),CORE.offset(-1,0,0))){
                scenarios++;l=new Level();place(b,l,CORE,f,p,new ItemStack(4));l.states.put(inside,b.defaultBlockState().setValue(DummyableBlock.FACING,f.getOpposite()));l.removeBlock(CORE,false);
                check(l.getBlockState(inside).getBlock()==b&&DummyableBlock.isCore(l.getBlockState(inside)),"unowned core inside the box preserved "+f+inside);
                check(l.getBlockState(CORE).getBlock()!=b,"the removed core is gone "+f+inside);
                for(BlockPos remaining:occupied(l,b))check(inside.equals(b.findCore(l,remaining)),"every surviving cell chains to the unowned core, none to the removed one "+f+inside+remaining);
            }
        }
        System.out.println("Goal18A structures: "+checks+" assertions; "+scenarios+" independent scenarios; 0 executed ticks");
    }
}
