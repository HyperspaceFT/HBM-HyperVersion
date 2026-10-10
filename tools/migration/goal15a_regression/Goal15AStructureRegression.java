package goal15a;

import java.util.*;

/** Engine-service world model exercising extracted production methods, not a game run. */
public class Goal15AStructureRegression {
    static int checks, blockedCells, teardownScenarios, replacementScenarios;
    static final BlockPos CORE = new BlockPos(0,64,0);
    static final Direction[] FACINGS = {Direction.NORTH,Direction.SOUTH,Direction.WEST,Direction.EAST};
    static void check(boolean value,String label) { checks++; if(!value) throw new AssertionError(label); }
    static Set<BlockPos> footprint(BlockPos core,Direction facing) {
        Set<BlockPos> result = new HashSet<>();
        // Original dimensions, independently expressed as inclusive local-coordinate ranges.
        for(int[] box : new int[][]{{-3,2,0,1,-1,0}}) {
            for(int x=box[0];x<=box[1];x++) for(int y=box[2];y<=box[3];y++) for(int z=box[4];z<=box[5];z++) {
                result.add(switch(facing) {
                    case SOUTH -> core.offset(x,y,z);
                    case NORTH -> core.offset(-x,y,-z);
                    case EAST -> core.offset(z,y,-x);
                    case WEST -> core.offset(-z,y,x);
                    default -> throw new AssertionError();
                });
            }
        }
        return result;
    }
    static Set<BlockPos> occupied(Level world,Block block) {
        Set<BlockPos> result=new HashSet<>();
        for(var entry:world.states.entrySet()) if(entry.getValue().getBlock()==block) result.add(entry.getKey());
        return result;
    }
    static void place(Engine block,Level world,BlockPos core,Direction facing,Player player,ItemStack stack) {
        BlockPos clicked=core;
        BlockState state=block.defaultBlockState().setValue(DummyableBlock.FACING,facing);
        world.states.put(clicked,state);
        block.setPlacedBy(world,clicked,state,player,stack);
        stack.consume(player);
    }
    public static void main(String[] args) {
        for(Direction facing:FACINGS) {
            Engine block=new Engine(); Level world=new Level(); Player player=new Player();
            ItemStack stack=new ItemStack(64);stack.components.put("custom","keep");
            Set<BlockPos> cells=footprint(CORE,facing);
            check(cells.size()==24,"finite original24cell footprint");
            place(block,world,CORE,facing,player,stack);
            check(occupied(world,block).equals(cells),"exact original engine-box placement "+facing);
            check(stack.count==63&&stack.components.equals(Map.of("custom","keep")),"successful original stack consumption");
            Set<BlockPos> extras=new HashSet<>();
            Direction side=switch(facing){case NORTH->Direction.EAST;case EAST->Direction.SOUTH;case SOUTH->Direction.WEST;case WEST->Direction.NORTH;default->throw new AssertionError();};
            Set<BlockPos> expectedExtras=Set.of(CORE.relative(side),CORE.relative(side.getOpposite()),CORE.relative(facing.getOpposite()).relative(side),CORE.relative(facing.getOpposite()).relative(side.getOpposite()));
            for(BlockPos cell:cells) {
                BlockState state=world.getBlockState(cell);
                check(CORE.equals(block.findCore(world,cell)),"cell reaches own core "+facing+cell);
                BlockEntity entity=block.newBlockEntity(cell,state);
                if(state.getValue(DummyableBlock.TYPE)==DummyBlockType.EXTRA) {
                    extras.add(cell);check(entity instanceof ProxyComboBlockEntity,"extra owns proxy");
                    ProxyComboBlockEntity proxy=(ProxyComboBlockEntity)entity;
                    check(proxy.power&&proxy.fluid,"extra exposes power and fluid roles");
                } else check(entity==null||cell.equals(CORE),"ordinary dummy has no entity");
            }
            check(extras.equals(expectedExtras),"exact four orientation-specific proxies");
            for(BlockPos obstacle:cells) {
                if(obstacle.equals(CORE)) continue;
                blockedCells++;
                Level bad=new Level();Block solid=new Block();bad.states.put(obstacle,solid.defaultBlockState());
                ItemStack refund=new ItemStack(64);refund.components.put("custom","keep");
                place(block,bad,CORE,facing,player,refund);
                check(refund.count==64&&refund.components.equals(Map.of("custom","keep")),"component-preserving at-limit refund "+obstacle);
                check(occupied(bad,block).isEmpty()&&bad.getBlockState(obstacle).getBlock()==solid,"obstruction leaves no partial machine "+obstacle);
            }
            for(boolean direct:new boolean[]{false,true}) for(BlockPos removed:cells) {
                teardownScenarios++;
                world=new Level();place(block,world,CORE,facing,player,new ItemStack(4));
                BlockPos adjacent=CORE.relative(side,6);place(block,world,adjacent,facing,player,new ItemStack(4));
                Set<BlockPos> neighbor=footprint(adjacent,facing);
                check(occupied(world,block).containsAll(neighbor),"neighbor placed before teardown");
                BlockState old=world.getBlockState(removed);
                if(!direct) block.playerWillDestroy(world,removed,old,player);
                world.removeBlock(removed,false);
                check(occupied(world,block).equals(neighbor),"each old-state/core/dummy/extra teardown preserves adjacent same machine "+facing+removed+direct);
                check(!DummyableBlock.safeRem,"removal guard restored");
            }
            // Level.setBlock publishes the new state before invoking oldState.onRemove, like the engine.
            for(BlockPos replaced:List.of(CORE,CORE.relative(side),CORE.relative(facing.getOpposite()).relative(side),CORE.above())) {
                replacementScenarios++;
                world=new Level();place(block,world,CORE,facing,player,new ItemStack(4));
                BlockPos adjacent=CORE.relative(side,6);place(block,world,adjacent,facing,player,new ItemStack(4));
                Block replacement=new Block();
                world.setBlock(replaced,replacement.defaultBlockState(),3);
                check(world.getBlockState(replaced).getBlock()==replacement,"non-air replacement survives old-state callback "+facing+replaced);
                check(occupied(world,block).equals(footprint(adjacent,facing)),"replacement clears only old owned engine "+facing+replaced);
                check(!DummyableBlock.safeRem,"replacement restores removal guard");
            }
            // A same-identity foreign core inside the geometric candidate box is not owned by this machine.
            world=new Level();place(block,world,CORE,facing,player,new ItemStack(4));
            BlockPos foreign=CORE.above();
            world.states.put(foreign,block.defaultBlockState().setValue(DummyableBlock.FACING,facing));
            world.removeBlock(CORE,false);
            check(world.getBlockState(foreign).getBlock()==block&&DummyableBlock.isCore(world.getBlockState(foreign)),"ownership guard preserves foreign core in candidate box");
            world=new Level();player.creative=true;ItemStack free=new ItemStack(9);
            place(block,world,CORE,facing,player,free);
            check(free.count==9&&occupied(world,block).equals(cells),"creative placement does not consume");
            player.creative=false;world=new Level();world.isClientSide=true;
            place(block,world,CORE,facing,player,new ItemStack(4));
            check(occupied(world,block).isEmpty(),"client does not create multiblock");
        }
        System.out.println("Goal15A structures: "+checks+" assertions; "+blockedCells+" obstructed-cell scenarios; "+teardownScenarios+" teardown scenarios; "+replacementScenarios+" non-air replacement scenarios; 4 orientations; engine-service model only.");
    }
}


