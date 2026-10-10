"""Bounded method-level world for the block lifecycle fixes.

The changed production methods are copied verbatim into compile shells. Minecraft
placement, removal and loot orchestration are modeled by BlockLifecycleRegression,
and checked against the locally cached merged source by the verifier. This is not
a Minecraft launch or a whole-class compilation. Inventory, position, NBT and
loot services below are minimal stand-ins; real APIs are checked by the main build.
"""

from pathlib import Path


def method(source, signature):
    start = source.index(signature)
    if source.find(signature, start + 1) >= 0:
        raise ValueError(f"ambiguous method: {signature}")
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    # These selected methods have no braces inside string literals.
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


BARREL = "com/hbm/blocks/machine/BarrelBlock.java"
DUMMY = "com/hbm/blocks/DummyableBlock.java"
BARREL_BE = "com/hbm/blockentity/machine/storage/BarrelBlockEntity.java"
BARREL_METHODS = (
    "public void onRemove(", "public void playerDestroy(",
    "public void onBlockExploded(", "protected void spawnAfterBreak(",
    "protected boolean hasAnalogOutputSignal(", "protected int getAnalogOutputSignal(",
    "protected List<ItemStack> getDrops(",
)

STUBS = r'''package reviewfixes;
import java.util.*;
@interface Nullable {}
record BlockPos(int x, int y, int z) {
    BlockPos above(int n) { return new BlockPos(x,y+n,z); }
    BlockPos relative(Direction d, int n) { return new BlockPos(x,y,z+n); }
}
enum Direction { NORTH }
class LivingEntity {}
class Player extends LivingEntity {
    final boolean creative;
    ItemStack main, off;
    final List<ItemStack> inventory = new ArrayList<>();
    Player(boolean creative, ItemStack main, ItemStack off) { this.creative=creative; this.main=main; this.off=off; }
    boolean hasInfiniteMaterials() { return creative; }
    ItemStack getMainHandItem() { return main; }
    ItemStack getOffhandItem() { return off; }
    void awardStat(Object stat) {}
    void causeFoodExhaustion(float amount) {}
}
class ItemStack {
    static final ItemStack EMPTY = new ItemStack(null,0);
    final Object item;
    int count;
    final Map<String,String> components = new LinkedHashMap<>();
    ItemStack(Object item) { this(item,1); }
    ItemStack(Object item,int count) { this.item=item; this.count=count; }
    ItemStack component(String key,String value) { components.put(key,value); return this; }
    int getCount() { return count; }
    int getMaxStackSize() { return 64; }
    boolean is(Object item) { return this.item==item; }
    boolean isEmpty() { return count==0; }
    void grow(int amount) { count+=amount; }
    void consume(int amount,Player player) { if(!player.hasInfiniteMaterials()) count-=amount; }
    ItemStack copy() { ItemStack s=new ItemStack(item,count); s.components.putAll(components); return s; }
}
class BlockEntity {}
interface BlockGetter { BlockEntity getBlockEntity(BlockPos pos); }
class Level implements BlockGetter {
    boolean isClientSide;
    BlockEntity be;
    final List<ItemStack> drops = new ArrayList<>();
    int inventoryDrops, placed, removed, scheduled;
    Map<String,String> restored;
    public BlockEntity getBlockEntity(BlockPos pos) { return be; }
    void removeBlock(BlockPos pos,boolean moving) { removed++; }
    void setBlock(BlockPos pos,BlockState state,int flags) { placed++; }
    void scheduleTick(BlockPos pos,Block block,int delay) { scheduled++; }
}
class ServerLevel extends Level {}
class Explosion {}
class BlockState {
    final Block block;
    BlockState(Block block) { this.block=block; }
    Block getBlock() { return block; }
    boolean is(Block block) { return this.block==block; }
    Direction getValue(Object property) { return Direction.NORTH; }
}
class LootParams { static class Builder {
    final Level level;
    Builder(Level level) { this.level=level; }
} }
class Block {
    Object asItem() { return this; }
    void setPlacedBy(Level level,BlockPos pos,BlockState state,LivingEntity placer,ItemStack stack) {}
    void onRemove(BlockState state,Level level,BlockPos pos,BlockState next,boolean moving) { level.be=null; }
    void playerDestroy(Level level,Player player,BlockPos pos,BlockState state,BlockEntity be,ItemStack tool) {}
    boolean canDropFromExplosion(BlockState state,BlockGetter level,BlockPos pos,Explosion explosion) { return true; }
    void onBlockExploded(BlockState state,Level level,BlockPos pos,Explosion explosion) {
        onRemove(state,level,pos,new BlockState(new Block()),false);
    }
    void spawnAfterBreak(BlockState state,ServerLevel level,BlockPos pos,ItemStack tool,boolean xp) {}
    boolean hasAnalogOutputSignal(BlockState state) { return false; }
    int getAnalogOutputSignal(BlockState state,Level level,BlockPos pos) { return 0; }
    List<ItemStack> getDrops(BlockState state,LootParams.Builder params) { return List.of(new ItemStack(this)); }
    static void popResource(Level level,BlockPos pos,ItemStack stack) { if(!level.isClientSide) level.drops.add(stack.copy()); }
}
class Containers {
    static void dropContents(Level level,BlockPos pos,BarrelBlockEntity barrel) { level.inventoryDrops+=barrel.inventory; barrel.inventory=0; }
}
class Stats { static final Stats BLOCK_MINED=new Stats(); Object get(Block b) { return b; } }
class Tank { int fill,max; Tank(int fill,int max) { this.fill=fill;this.max=max; } int getFill(){return fill;} int getMaxFill(){return max;} }
class IPersistentNBT {
    static List<ItemStack> getDropsFromLootParams(BlockState state,LootParams.Builder params) {
        return params.level.be instanceof BarrelBlockEntity barrel ? barrel.getDrops(state.getBlock()) : List.of();
    }
    static void restoreData(Level level,BlockPos pos,ItemStack stack) { level.restored=new LinkedHashMap<>(stack.components); }
}
class BarrelBlockEntity extends BlockEntity {
    private boolean shouldDrop=true;
    final Tank tank;
    int inventory=2;
    BarrelBlockEntity(int fill,int max) { tank=new Tank(fill,max); }
    List<ItemStack> getDrops(Block block) {
        ItemStack body=new ItemStack(block);
        if(tank.fill>0) body.component("persistent.tank.type","water").component("persistent.tank.fill",Integer.toString(tank.fill));
        return List.of(body);
    }
    __BARREL_BE_METHODS__
}
class ReviewedBarrel extends Block {
    final boolean corroded;
    ReviewedBarrel(boolean corroded) { this.corroded=corroded; }
    __BARREL_METHODS__
}
class ReviewedDummy extends Block {
    static boolean safeRem;
    static final Object FACING=new Object();
    boolean space=true;
    int getOffset() { return 1; }
    int getHeightOffset() { return 0; }
    Direction getDirModified(Direction dir) { return dir; }
    boolean checkRequirement(Level level,BlockPos pos,Direction dir,int offset) { return space; }
    BlockState getStateForCore(Level level,BlockPos pos,Player player,Direction dir) { return new BlockState(this); }
    void fillSpace(Level level,BlockPos pos,Direction dir,int offset) {}
    __DUMMY_METHOD__
}
'''


def build_world(source: Path):
    barrel = (source / BARREL).read_text(encoding="utf-8")
    dummy = (source / DUMMY).read_text(encoding="utf-8")
    be = (source / BARREL_BE).read_text(encoding="utf-8")
    return (STUBS.replace("__BARREL_METHODS__", "\n".join(method(barrel, s) for s in BARREL_METHODS))
            .replace("__DUMMY_METHOD__", method(dummy, "public void setPlacedBy("))
            .replace("__BARREL_BE_METHODS__", "\n".join(method(be, s) for s in
                ("public boolean shouldDrop(", "public void preventDrop(", "public byte getComparatorPower("))))
