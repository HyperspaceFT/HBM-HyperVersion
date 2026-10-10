"""Method-level structural world, not Minecraft or a full production-class build.

Bodies of placement, shape, neighbor, ownership and teardown methods are taken
verbatim from production. Registry/codec/rendering/loot/entity services are
stand-ins. Level models old-state onRemove after state replacement; block-item
consumption follows the locally cached engine contract. Collision traversal and
ray casting remain real-game acceptance tasks.
"""
from pathlib import Path
import re
from review_fixes.block_stubs import method

WORLD = r'''package goal14b;
import java.util.*;
@interface Nullable {}
record BlockPos(int x,int y,int z) {
 int getX(){return x;} int getY(){return y;} int getZ(){return z;}
 BlockPos offset(int a,int b,int c){return new BlockPos(x+a,y+b,z+c);}
 BlockPos above(){return above(1);} BlockPos above(int n){return offset(0,n,0);} BlockPos below(){return above(-1);}
 BlockPos relative(Direction d){return relative(d,1);} BlockPos relative(Direction d,int n){return offset(d.dx*n,d.dy*n,d.dz*n);}
}
enum Direction { DOWN(0,-1,0),UP(0,1,0),NORTH(0,0,-1),SOUTH(0,0,1),WEST(-1,0,0),EAST(1,0,0);
 enum Axis{X,Y,Z} int dx,dy,dz; Direction(int x,int y,int z){dx=x;dy=y;dz=z;}
 Direction getOpposite(){return values()[ordinal()^1];}
}
class Property<T>{}
class IntegerProperty extends Property<Integer>{
 final int min,max;IntegerProperty(int a,int b){if(a<0||b<=a)throw new IllegalArgumentException("invalid integer property bounds");min=a;max=b;}
 static IntegerProperty create(String n,int a,int b){return new IntegerProperty(a,b);}
}
class Vec3{final double x,y,z;Vec3(double x,double y,double z){this.x=x;this.y=y;this.z=z;}}
class CollisionContext{}
class VoxelShape {
 final double[] b; VoxelShape(double... b){this.b=b;} boolean isEmpty(){return b.length==0;}
 double min(Direction.Axis a){return b[a.ordinal()];} double max(Direction.Axis a){return b[a.ordinal()+3];}
}
class Shapes{static VoxelShape empty(){return new VoxelShape();}}
class StateDefinition {Block owner; StateDefinition(Block b){owner=b;} BlockState any(){return new BlockState(owner);}}
class BlockState {
 final Block block; final Map<Property<?>,Object> values=new HashMap<>(); BlockState(Block b){block=b;}
 <T> BlockState setValue(Property<T> p,T v){BlockState s=new BlockState(block);s.values.putAll(values);s.values.put(p,v);return s;}
 @SuppressWarnings("unchecked") <T>T getValue(Property<T> p){return (T)values.get(p);}
 Block getBlock(){return block;} boolean is(Block b){return block==b;} boolean isAir(){return block==Block.AIR;}
 boolean canBeReplaced(){return isAir();}
 VoxelShape getCollisionShape(BlockGetter l,BlockPos p){return block.getCollisionShape(this,l,p,new CollisionContext());}
}
interface BlockGetter{BlockState getBlockState(BlockPos p);}
class Level implements BlockGetter {
 boolean isClientSide; final Map<BlockPos,BlockState> states=new HashMap<>(); int drops,scheduled; boolean throwRemove;
 public BlockState getBlockState(BlockPos p){return states.getOrDefault(p,Block.AIR.defaultBlockState());}
 void setBlock(BlockPos p,BlockState s,int flags){BlockState old=getBlockState(p);states.put(p,s);if(old.getBlock()!=s.getBlock())old.getBlock().onRemove(old,this,p,s,false);}
 void removeBlock(BlockPos p,boolean moving){if(throwRemove)throw new RuntimeException("fixture removal failure");setBlock(p,Block.AIR.defaultBlockState(),3);states.remove(p);}
 void destroyBlock(BlockPos p,boolean drop){if(drop)drops++;removeBlock(p,false);}
 void scheduleTick(BlockPos p,Block b,int n){scheduled++;}
}
class LivingEntity{}
class Player extends LivingEntity {boolean creative,sneak; boolean hasInfiniteMaterials(){return creative;} boolean isShiftKeyDown(){return sneak;}}
class ItemStack {int count;Map<String,String> components=new HashMap<>();ItemStack(int n){count=n;}void grow(int n){count+=n;}void consume(Player p){if(!p.creative)count--;}}
class BlockPlaceContext {
 final Level level;final BlockPos pos;final Direction face;final double y;final Player player;
 BlockPlaceContext(Level l,BlockPos p,Direction f,double y,Player pl){level=l;pos=p;face=f;this.y=y;player=pl;}
 Level getLevel(){return level;} BlockPos getClickedPos(){return pos;}Direction getClickedFace(){return face;}
 Vec3 getClickLocation(){return new Vec3(pos.x()+.5,pos.y()+y,pos.z()+.5);} Player getPlayer(){return player;}
}
class IPersistentNBT {static void restoreData(Level l,BlockPos p,ItemStack s){}}
class Containers {static void dropContentsOnDestroy(BlockState a,BlockState b,Level l,BlockPos p){}}
class Block {
 static final Block AIR=new Block(); final StateDefinition stateDefinition=new StateDefinition(this);BlockState defaultState=new BlockState(this);
 BlockState defaultBlockState(){return defaultState;}void registerDefaultState(BlockState s){defaultState=s;}
 static VoxelShape box(double a,double b,double c,double d,double e,double f){return new VoxelShape(a/16,b/16,c/16,d/16,e/16,f/16);}
 VoxelShape getShape(BlockState s,BlockGetter l,BlockPos p,CollisionContext c){return s.isAir()?Shapes.empty():box(0,0,0,16,16,16);}
 VoxelShape getCollisionShape(BlockState s,BlockGetter l,BlockPos p,CollisionContext c){return getShape(s,l,p,c);}
 BlockState playerWillDestroy(Level l,BlockPos p,BlockState s,Player pl){return s;}
 void onRemove(BlockState s,Level l,BlockPos p,BlockState n,boolean moving){}
 void setPlacedBy(Level l,BlockPos p,BlockState s,LivingEntity pl,ItemStack st){}
}
enum DummyBlockType{CORE,DUMMY,EXTRA}
class DummyableBlock extends Block {
 static boolean safeRem;static final Property<Direction> FACING=new Property<>();static final Property<DummyBlockType> TYPE=new Property<>();
 final List<BlockPos> positions=new ArrayList<>();
 DummyableBlock(){registerDefaultState(defaultBlockState().setValue(FACING,Direction.NORTH).setValue(TYPE,DummyBlockType.CORE));}
 int[] getDimensions(){return null;}int getOffset(){return 1;}int getHeightOffset(){return 0;}
 Direction getDirModified(Direction d){return d;}BlockState getStateForCore(Level l,BlockPos p,Player pl,Direction d){return defaultBlockState().setValue(FACING,d);}
 static boolean isCore(BlockState s){return s.getValue(TYPE)==DummyBlockType.CORE;}
 static Direction getPointingDirection(BlockState s){return s.getValue(FACING);}
 __DUMMY__
}
class MultiblockHandlerXR {
 __XR__
}
class NuclearTechMod {static final Logger LOGGER=new Logger();static class Logger{void warn(String s,Object...args){}}}
record DirPos(BlockPos pos){BlockPos makeCompat(){return pos;}}
class MachineFractionTowerBlockEntity {
 static List<DirPos> getPortProxies(BlockPos p){return List.of(new DirPos(p.relative(Direction.EAST)),new DirPos(p.relative(Direction.WEST)),new DirPos(p.relative(Direction.SOUTH)),new DirPos(p.relative(Direction.NORTH)));}
}
class Tower extends DummyableBlock {__TOWER__}
class Spacer extends DummyableBlock {__SPACER__}
class SteelBeamBlock extends Block {__COLUMN__ __BEAM__}
class SteelGrateBlock extends Block {
 __HEIGHT__ private static final VoxelShape[] SHAPES=new VoxelShape[10];
 static {__SHAPES__}
 SteelGrateBlock(){registerDefaultState(defaultBlockState().setValue(HEIGHT,0));}
 __GRATE__
}
'''

def build_world(source: Path):
    def read(path): return (source / path).read_text(encoding="utf-8")
    def bodies(path, signatures):
        text = read(path)
        return "\n".join(method(text, signature) for signature in signatures)
    dummy = bodies("com/hbm/blocks/DummyableBlock.java", (
        "public BlockPos findCore(", "private BlockPos findCoreRecursive(", "public void setPlacedBy(",
        "protected boolean checkRequirement(", "protected void fillSpace(", "public void makeExtra(", "public void onRemove("))
    xr = bodies("com/hbm/handler/MultiblockHandlerXR.java", (
        "public static boolean checkSpace(", "public static void fillSpace(", "public static int[] rotate("))
    tower = bodies("com/hbm/blocks/machine/MachineFractionTowerBlock.java", (
        "public int[] getDimensions(", "public int getOffset(", "protected void fillSpace(",
        "public BlockState playerWillDestroy(", "public void onRemove(", "private void destroyTower(", "private BlockPos findOwnedCore("))
    spacer = bodies("com/hbm/blocks/machine/FractionSpacerBlock.java", (
        "public int[] getDimensions(", "public int getOffset(", "public BlockState playerWillDestroy(",
        "public void onRemove(", "private void destroySpacer(", "private BlockPos findOwnedCore("))
    beam = bodies("com/hbm/blocks/generic/SteelBeamBlock.java", ("protected VoxelShape getShape(", "protected VoxelShape getCollisionShape("))
    column = re.search(r"private static final VoxelShape COLUMN\s*=.*?;", read("com/hbm/blocks/generic/SteelBeamBlock.java")).group()
    height = re.search(r"public static final IntegerProperty HEIGHT\s*=.*?;", read("com/hbm/blocks/generic/SteelGrateBlock.java")).group()
    grate = bodies("com/hbm/blocks/generic/SteelGrateBlock.java", (
        "public BlockState getStateForPlacement(", "private static boolean hasOffsetClearance(",
        "public void neighborChanged(", "protected VoxelShape getShape(", "protected VoxelShape getCollisionShape(", "protected VoxelShape getBlockSupportShape("))
    shapes = method(read("com/hbm/blocks/generic/SteelGrateBlock.java"), "static {")[len("static {"):-1]
    # Access modifiers of the selected bodies match the shells. Nullable is a modeled marker.
    return (WORLD.replace("__DUMMY__", dummy).replace("__XR__", xr).replace("__TOWER__", tower)
            .replace("__SPACER__", spacer).replace("__BEAM__", beam).replace("__GRATE__", grate)
            .replace("__SHAPES__", shapes).replace("__COLUMN__", column).replace("__HEIGHT__", height))
