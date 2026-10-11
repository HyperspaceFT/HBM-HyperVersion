package goal17b;
import java.util.*;

/** Extracted production structure/lifecycle methods; engine inventory/loot is a service. */
public class Goal17BStructureRegression {
    static int checks,scenarios;
    static final BlockPos CORE=new BlockPos(0,64,0);
    static final Direction[] FACINGS={Direction.NORTH,Direction.SOUTH,Direction.WEST,Direction.EAST};
    static void check(boolean v,String s){checks++;if(!v)throw new AssertionError(s);}
    static Set<BlockPos> footprint(BlockPos p,Direction facing){
        Set<BlockPos> cells=new HashSet<>();
        for(int x=-3;x<=3;x++)for(int y=0;y<=2;y++)for(int z=-1;z<=1;z++)
            cells.add(switch(facing){case NORTH,SOUTH->p.offset(x,y,z);case EAST,WEST->p.offset(z,y,x);default->throw new AssertionError();});
        return cells;
    }
    static Set<BlockPos> occupied(Level l,Block b){Set<BlockPos> s=new HashSet<>();for(var e:l.states.entrySet())if(e.getValue().getBlock()==b)s.add(e.getKey());return s;}
    static void place(Turbofan b,Level l,BlockPos core,Direction f,Player p,ItemStack stack){
        BlockPos clicked=core.relative(f);BlockState s=b.defaultBlockState().setValue(DummyableBlock.FACING,f);
        l.states.put(clicked,s);b.setPlacedBy(l,clicked,s,p,stack);stack.consume(p);
    }
    public static void main(String[] args){
        for(Direction f:FACINGS){
            scenarios++;var b=new Turbofan();Level l=new Level();Player p=new Player();ItemStack stack=new ItemStack(64);stack.components.put("custom","keep");
            Set<BlockPos> cells=footprint(CORE,f);place(b,l,CORE,f,p,stack);
            check(cells.size()==63&&occupied(l,b).equals(cells),"original3x3x7 box "+f);
            check(stack.count==63&&stack.components.equals(Map.of("custom","keep")),"component preserving placement");
            Direction intake=switch(f){case NORTH->Direction.EAST;case EAST->Direction.SOUTH;case SOUTH->Direction.WEST;case WEST->Direction.NORTH;default->throw new AssertionError();};
            Set<BlockPos> expected=Set.of(CORE.relative(f),CORE.relative(f).relative(intake.getOpposite()),CORE.relative(f.getOpposite()),CORE.relative(f.getOpposite()).relative(intake.getOpposite()));
            Set<BlockPos> extras=new HashSet<>();
            for(BlockPos cell:cells){
                check(CORE.equals(b.findCore(l,cell)),"owned core reachability "+f+cell);
                BlockState s=l.getBlockState(cell);BlockEntity entity=b.newBlockEntity(cell,s);
                if(s.getValue(DummyableBlock.TYPE)==DummyBlockType.EXTRA){
                    extras.add(cell);check(entity instanceof ProxyComboBlockEntity&&((ProxyComboBlockEntity)entity).fluid&&((ProxyComboBlockEntity)entity).power,"proxy fluid and power");
                }else check(entity==null||cell.equals(CORE),"no dummy BE");
            }
            check(extras.equals(expected),"exact four proxies "+f);
            for(DirPos proxy:MachineTurbofanBlockEntity.getPortProxies(CORE,f)){
                BlockPos external=proxy.makeCompat().relative(proxy.getDir());
                check(!cells.contains(external)&&external.equals(proxy.makeCompat().relative(proxy.getDir())),"external neighbor outside structure");
            }
            for(BlockPos obstacle:cells){
                if(obstacle.equals(CORE.relative(f)))continue;
                scenarios++;Level bad=new Level();Block solid=new Block();bad.states.put(obstacle,solid.defaultBlockState());ItemStack refund=new ItemStack(64);refund.components.put("custom","keep");place(b,bad,CORE,f,p,refund);
                check(refund.count==64&&refund.components.equals(Map.of("custom","keep")),"blocked at-limit refund keeps components");
                check(occupied(bad,b).isEmpty()&&bad.getBlockState(obstacle).getBlock()==solid,"blocked no partial structure");
            }
            for(boolean direct:new boolean[]{false,true})for(BlockPos removed:cells){
                scenarios++;l=new Level();place(b,l,CORE,f,p,new ItemStack(4));BlockPos neighbor=CORE.relative(f,5);place(b,l,neighbor,f,p,new ItemStack(4));
                BlockState old=l.getBlockState(removed);if(!direct)b.playerWillDestroy(l,removed,old,p);l.removeBlock(removed,false);
                check(occupied(l,b).equals(footprint(neighbor,f)),"teardown preserves independent neighbor "+f+removed);
                check(l.inventoryDrops==1&&!DummyableBlock.safeRem,"inventory once guard restored");
                if(!direct)check(l.drops==1,"survival machine loot once");
            }
            for(BlockPos replaced:List.of(CORE,CORE.relative(f),CORE.relative(f.getOpposite()).relative(intake.getOpposite()),CORE.above())){
                scenarios++;l=new Level();place(b,l,CORE,f,p,new ItemStack(4));BlockPos neighbor=CORE.relative(f,5);place(b,l,neighbor,f,p,new ItemStack(4));Block replacement=new Block();l.setBlock(replaced,replacement.defaultBlockState(),3);
                check(l.getBlockState(replaced).getBlock()==replacement&&occupied(l,b).equals(footprint(neighbor,f)),"nonair replacement preserved with neighbor");
                check(l.inventoryDrops==1&&!DummyableBlock.safeRem,"replace inventory once");
            }
            scenarios++;l=new Level();place(b,l,CORE,f,p,new ItemStack(4));BlockPos foreign=CORE.above();l.states.put(foreign,b.defaultBlockState().setValue(DummyableBlock.FACING,f));l.removeBlock(CORE,false);
            check(l.getBlockState(foreign).getBlock()==b&&DummyableBlock.isCore(l.getBlockState(foreign)),"foreign core inside candidate box preserved");
        }
        System.out.println("Goal17B structures: "+checks+" assertions; "+scenarios+" independent scenarios; 0 executed ticks");
    }
}
