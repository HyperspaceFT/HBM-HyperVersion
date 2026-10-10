package goal14b;

import java.util.*;

/** Isolated production-method checks; no engine collision traversal, rendering, ray casting or game loading. */
public class Goal14BStructureRegression {
    static int checks;
    static void check(boolean value,String message) { checks++; if(!value) throw new AssertionError(message); }
    static void near(double a,double b,String message) { check(Math.abs(a-b)<1E-9,message+": "+a+" != "+b); }
    static final BlockPos ORIGIN=new BlockPos(0,64,0);

    static void shapes() {
        Level level=new Level(); CollisionContext context=new CollisionContext();
        SteelBeamBlock beam=new SteelBeamBlock();
        VoxelShape selected=beam.getShape(beam.defaultBlockState(),level,ORIGIN,context);
        VoxelShape collision=beam.getCollisionShape(beam.defaultBlockState(),level,ORIGIN,context);
        check(Arrays.equals(selected.b,collision.b),"beam collision equals selection");
        check(Arrays.equals(selected.b,new double[]{7D/16,0,7D/16,9D/16,1,9D/16}),"original narrow beam dimensions");
        SteelGrateBlock grate=new SteelGrateBlock();
        for(int h=-1;h<=8;h++) {
            BlockState state=grate.defaultBlockState().setValue(SteelGrateBlock.HEIGHT,h==-1?9:h);
            VoxelShape shape=grate.getShape(state,level,ORIGIN,context);
            near(shape.min(Direction.Axis.Y),h/8D,"grate lower bound "+h);
            near(shape.max(Direction.Axis.Y),(h+1)/8D,"grate upper bound "+h);
            check(Arrays.equals(shape.b,grate.getCollisionShape(state,level,ORIGIN,context).b),"grate selection/collision "+h);
            check(grate.getBlockSupportShape(state,level,ORIGIN).isEmpty()==(h!=0&&h!=7),"support only boundary states "+h);
        }
        Player player=new Player();
        for(Direction face:Direction.values()) for(double y:new double[]{0,.124999,.125,.4999,.875,.999999,1}) {
            int actual=grate.getStateForPlacement(new BlockPlaceContext(level,ORIGIN,face,y,player)).getValue(SteelGrateBlock.HEIGHT);
            int expected=face==Direction.UP?0:face==Direction.DOWN?7:(int)Math.floor(y*8);
            check(actual==expected,"non-sneak placement "+face+" "+y);
        }
        player.sneak=true;
        Block partial=new Block(){@Override VoxelShape getCollisionShape(BlockState s,BlockGetter l,BlockPos p,CollisionContext c){return box(0,0,0,16,14,16);}};
        level.states.put(ORIGIN.below(),partial.defaultBlockState());
        check(grate.getStateForPlacement(new BlockPlaceContext(level,ORIGIN,Direction.UP,0,player)).getValue(SteelGrateBlock.HEIGHT)==9,"sneak below partial collision");
        Block upper=new Block(){@Override VoxelShape getCollisionShape(BlockState s,BlockGetter l,BlockPos p,CollisionContext c){return box(0,2,0,16,16,16);}};
        level.states.put(ORIGIN.above(),upper.defaultBlockState());
        check(grate.getStateForPlacement(new BlockPlaceContext(level,ORIGIN,Direction.DOWN,1,player)).getValue(SteelGrateBlock.HEIGHT)==8,"sneak above partial collision");
        for(int h:new int[]{-1,8}) {
            BlockPos neighbor=h==-1?ORIGIN.below():ORIGIN.above();
            for(double bound:new double[]{.049,.05,.051,.949,.95,.951}) {
                Block test=new Block(){@Override VoxelShape getCollisionShape(BlockState s,BlockGetter l,BlockPos p,CollisionContext c){return h==-1?new VoxelShape(0,0,0,1,bound,1):new VoxelShape(0,bound,0,1,1,1);}};
                level=new Level();level.states.put(neighbor,test.defaultBlockState());
                BlockState state=grate.defaultBlockState().setValue(SteelGrateBlock.HEIGHT,h==-1?9:h);level.states.put(ORIGIN,state);
                grate.neighborChanged(state,level,ORIGIN,test,neighbor,false);
                boolean clear=h==-1?bound<.95:bound>.05;
                check(level.getBlockState(ORIGIN).isAir()==!clear,"strict neighbor threshold "+h+" "+bound);
                check(level.drops==(clear?0:1),"neighbor drop exactly once "+h+" "+bound);
            }
            level=new Level();BlockState state=grate.defaultBlockState().setValue(SteelGrateBlock.HEIGHT,h==-1?9:h);level.states.put(ORIGIN,state);
            grate.neighborChanged(state,level,ORIGIN,Block.AIR,neighbor,false);
            check(level.getBlockState(ORIGIN)==state&&level.drops==0,"air neighbor retains offset grate "+h);
            level.isClientSide=true;level.states.put(neighbor,new Block().defaultBlockState());
            grate.neighborChanged(state,level,ORIGIN,level.getBlockState(neighbor).getBlock(),neighbor,false);
            check(level.getBlockState(ORIGIN)==state,"client never destroys grate "+h);
        }
    }

    static BlockPos place(DummyableBlock block,Level level,BlockPos core,Direction facing,Player player,ItemStack stack) {
        BlockPos clicked=core.relative(facing,block.getOffset());
        BlockState state=block.defaultBlockState().setValue(DummyableBlock.FACING,facing);
        level.states.put(clicked,state);block.setPlacedBy(level,clicked,state,player,stack);stack.consume(player);return clicked;
    }
    static Set<BlockPos> footprint(BlockPos core,int high) {
        Set<BlockPos> result=new HashSet<>();for(int x=-1;x<=1;x++)for(int y=0;y<high;y++)for(int z=-1;z<=1;z++)result.add(core.offset(x,y,z));return result;
    }
    static Set<BlockPos> occupied(Level level,Block block) {
        Set<BlockPos> result=new HashSet<>();for(var entry:level.states.entrySet())if(entry.getValue().getBlock()==block)result.add(entry.getKey());return result;
    }
    static void structures() {
        for(boolean tower:new boolean[]{false,true}) for(Direction facing:new Direction[]{Direction.NORTH,Direction.SOUTH,Direction.WEST,Direction.EAST}) {
            DummyableBlock block=tower?new Tower():new Spacer();int high=tower?3:1;
            Level level=new Level();Player player=new Player();ItemStack stack=new ItemStack(5);stack.components.put("custom","keep");
            place(block,level,ORIGIN,facing,player,stack);
            check(occupied(level,block).equals(footprint(ORIGIN,high)),"exact footprint "+tower+facing);
            check(stack.count==4&&stack.components.equals(Map.of("custom","keep")),"success consumes original component stack");
            for(BlockPos pos:footprint(ORIGIN,high))check(ORIGIN.equals(block.findCore(level,pos)),"every cell finds own core "+tower+facing+pos);
            Set<BlockPos> extra=new HashSet<>();for(BlockPos pos:occupied(level,block))if(level.getBlockState(pos).getValue(DummyableBlock.TYPE)==DummyBlockType.EXTRA)extra.add(pos);
            check(extra.equals(tower?Set.of(ORIGIN.relative(Direction.NORTH),ORIGIN.relative(Direction.SOUTH),ORIGIN.relative(Direction.EAST),ORIGIN.relative(Direction.WEST)):Set.of()),"exact proxies");
            for(BlockPos obstruction:footprint(ORIGIN,high)) {
                BlockPos clicked=ORIGIN.relative(facing,1);if(obstruction.equals(clicked))continue;
                Level bad=new Level();Block solid=new Block();bad.states.put(obstruction,solid.defaultBlockState());ItemStack refund=new ItemStack(64);refund.components.put("custom","keep");
                place(block,bad,ORIGIN,facing,player,refund);
                check(refund.count==64&&refund.components.equals(Map.of("custom","keep")),"obstruction exact refund at "+obstruction);
                check(occupied(bad,block).isEmpty()&&bad.getBlockState(obstruction).getBlock()==solid&&bad.scheduled==0,"obstruction leaves neighbor and no partial structure");
            }
            // Same-type adjacent and stacked structures, plus the other identity, must survive removing one segment.
            for(boolean direct:new boolean[]{false,true}) for(BlockPos broken:new BlockPos[]{ORIGIN,ORIGIN.offset(-1,0,-1),ORIGIN.above(high-1)}) {
                level=new Level();place(block,level,ORIGIN,facing,player,new ItemStack(5));
                BlockPos adjacent=ORIGIN.offset(3,0,0),stacked=ORIGIN.above(high);
                place(block,level,adjacent,facing,player,new ItemStack(5));place(block,level,stacked,facing,player,new ItemStack(5));
                DummyableBlock other=tower?new Spacer():new Tower();BlockPos otherCore=ORIGIN.offset(0,0,3);place(other,level,otherCore,facing,player,new ItemStack(5));
                BlockState old=level.getBlockState(broken);
                if(direct)level.removeBlock(broken,false);else {block.playerWillDestroy(level,broken,old,player);level.removeBlock(broken,false);}
                Set<BlockPos> expected=footprint(adjacent,high);expected.addAll(footprint(stacked,high));
                check(occupied(level,block).equals(expected),"bounded teardown "+tower+facing+direct+broken);
                check(occupied(level,other).equals(footprint(otherCore,tower?1:3)),"other identity unchanged");
                check(!DummyableBlock.safeRem,"guard restored after teardown");
            }
            level=new Level();level.isClientSide=true;ItemStack client=new ItemStack(4);place(block,level,ORIGIN,facing,player,client);
            check(occupied(level,block).isEmpty(),"client does not build multiblock");
            // A missing cell must not allow footprint guessing or removal of a neighbouring core.
            level=new Level();place(block,level,ORIGIN,facing,player,new ItemStack(5));
            level.states.remove(ORIGIN.offset(1,0,0));
            BlockPos adjacent=ORIGIN.offset(3,0,0);place(block,level,adjacent,facing,player,new ItemStack(5));
            Set<BlockPos> remaining=occupied(level,block);
            for(BlockPos pos:new HashSet<>(remaining))if(ORIGIN.equals(block.findCore(level,pos)))remaining.remove(pos);
            block.playerWillDestroy(level,ORIGIN,level.getBlockState(ORIGIN),player);
            check(occupied(level,block).equals(remaining)&&occupied(level,block).containsAll(footprint(adjacent,high)),"partial resolvable footprint cleared, adjacent remains; orphan callbacks not modeled");
            BlockPos orphan=ORIGIN.offset(2,0,0);BlockState orphanState=block.defaultBlockState().setValue(DummyableBlock.TYPE,DummyBlockType.DUMMY).setValue(DummyableBlock.FACING,Direction.EAST);
            level.states.put(orphan,orphanState);Set<BlockPos> before=occupied(level,block);
            block.playerWillDestroy(level,orphan,orphanState,player);
            check(occupied(level,block).equals(before),"orphan without core never guesses footprint");
            level=new Level();player.creative=true;ItemStack free=new ItemStack(9);place(block,level,ORIGIN,facing,player,free);
            check(free.count==9&&occupied(level,block).equals(footprint(ORIGIN,high)),"creative no consume");
            player.creative=false;
        }
    }
    public static void main(String[] args) {shapes();structures();System.out.println("Goal14B structures: "+checks+" checks passed; method world only.");}
}
