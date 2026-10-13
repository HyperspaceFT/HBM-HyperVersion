"""Bounded method-level world for the tool-ability harvest fix.

The production harvest path is copied verbatim into compile shells: the harvest
handlers of IToolHarvestAbility, the mining entry points of ToolAbilityItem, the
vein/hammer area handlers of IToolAreaAbility, the barrel and crate block and
block-entity drop methods, IPersistentNBT and CompatExternal.getCoreFromPos. Minecraft and
NeoForge block breaking (ServerPlayerGameMode.destroyBlock, Level.setBlock/destroyBlock,
LevelChunk.setBlockState, BlockBehaviour.onRemove, Block.getDrops/dropResources,
the vanilla explosion drop pass) is modeled below and in AbilityHarvestRegression.java;
the verifier checks that order against the cached NeoForge sources. Loot, NBT,
enchantment, recipe and config services are minimal stand-ins. This is not a Minecraft
launch or a whole-class compilation; the real APIs are checked by the main build.
"""

from pathlib import Path


def method(source, signature):
    start = source.index(signature)
    if source.find(signature, start + 1) >= 0:
        raise ValueError(f"ambiguous method: {signature}")
    return source[start:closing(source, source.index("{", start)) + 1]


def declaration(source, anchor):
    """An anonymous-class constant such as `IToolHarvestAbility SILK = new IToolHarvestAbility() {...};`."""
    start = source.index(anchor)
    if source.find(anchor, start + 1) >= 0:
        raise ValueError(f"ambiguous declaration: {anchor}")
    end = closing(source, source.index("{", start)) + 1
    assert source[end] == ";", f"declaration does not end with ';': {anchor}"
    return source[start:end + 1]


def region(source, first, last):
    """From the start of `first` to the end of `last`, both unique."""
    start = source.index(first)
    end = source.index(last, start) + len(last)
    assert source.count(first) == 1 and source.count(last) == 1, f"ambiguous region: {first} .. {last}"
    return source[start:end]


def closing(source, opening):
    # The copied production code has no braces inside string or character literals.
    depth = 0
    for index in range(opening, len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return index
    raise ValueError("unbalanced braces")


HARVEST = "com/hbm/handler/ability/IToolHarvestAbility.java"
AREA = "com/hbm/handler/ability/IToolAreaAbility.java"
TOOL = "com/hbm/items/tools/ToolAbilityItem.java"
BARREL = "com/hbm/blocks/machine/BarrelBlock.java"
BARREL_BE = "com/hbm/blockentity/machine/storage/BarrelBlockEntity.java"
CRATE = "com/hbm/blocks/machine/CrateBlock.java"
CRATE_BE = "com/hbm/blockentity/machine/storage/CrateBaseBlockEntity.java"
PERSISTENT = "com/hbm/blockentity/IPersistentNBT.java"
COMPAT = "com/hbm/util/CompatExternal.java"
PRODUCTION = (HARVEST, AREA, TOOL, BARREL, BARREL_BE, CRATE, CRATE_BE, PERSISTENT, COMPAT)

TOOL_METHODS = (
    "public boolean mineBlock(", "public float getDestroySpeed(", "public boolean isCorrectToolForDrops(ItemStack",
    "private boolean isEffectiveForState(", "public static boolean canTakeDamage(", "public static void damageTool(",
    "public boolean canOperate(", "public boolean canHarvest(", "public boolean canShearBlock(",
    "public boolean isShears(", "public void breakExtraBlock(",
)
BARREL_METHODS = (
    "public BlockEntity newBlockEntity(", "public void onRemove(", "public void playerDestroy(",
    "protected void spawnAfterBreak(", "protected List<ItemStack> getDrops(", "public void onBlockExploded(",
)
BARREL_BE_METHODS = ("public void writeNBT(", "public void readNBT(", "public boolean shouldDrop(", "public void preventDrop(")
CRATE_METHODS = ("public void onRemove(", "public void playerDestroy(", "protected void spawnAfterBreak(", "protected List<ItemStack> getDrops(")
CRATE_BE_METHODS = ("public void writeNBT(", "public boolean shouldDrop(", "public void preventDrop(")
AREA_HANDLERS = ("NONE", "RECURSION", "HAMMER", "HAMMER_FLAT")

STUBS = r'''package abilityharvest;
import java.util.*;
import java.util.function.*;
@interface Nullable {}
record BlockPos(int x, int y, int z) {
    int getX() { return x; }
    int getY() { return y; }
    int getZ() { return z; }
    BlockPos offset(BlockPos o) { return new BlockPos(x + o.x, y + o.y, z + o.z); }
    static BlockPos containing(double x, double y, double z) { return new BlockPos((int) Math.floor(x), (int) Math.floor(y), (int) Math.floor(z)); }
}
final class Vec3 {
    final double x, y, z;
    Vec3(double x, double y, double z) { this.x = x; this.y = y; this.z = z; }
    static Vec3 atCenterOf(BlockPos p) { return new Vec3(p.getX() + 0.5, p.getY() + 0.5, p.getZ() + 0.5); }
    double length() { return Math.sqrt(x * x + y * y + z * z); }
    Vec3 add(Vec3 o) { return new Vec3(x + o.x, y + o.y, z + o.z); }
    Vec3 scale(double f) { return new Vec3(x * f, y * f, z * f); }
}
enum Direction { DOWN, UP, NORTH, SOUTH, WEST, EAST }
enum EquipmentSlot { MAINHAND }
final class TagKey { final String id; TagKey(String id) { this.id = id; } }
final class BlockTags {
    static final TagKey MINEABLE_WITH_PICKAXE = new TagKey("mineable/pickaxe");
    static final TagKey MINEABLE_WITH_AXE = new TagKey("mineable/axe");
    static final TagKey MINEABLE_WITH_SHOVEL = new TagKey("mineable/shovel");
    static final TagKey MINEABLE_WITH_HOE = new TagKey("mineable/hoe");
}
class Entity {}
class LivingEntity extends Entity {}
class Player extends LivingEntity {
    final Level level;
    ItemStack main;
    int stats;
    Player(Level level, ItemStack main) { this.level = level; this.main = main; }
    ItemStack getMainHandItem() { return main; }
    Level level() { return level; }
    boolean hasCorrectToolForDrops(BlockState state) { return !state.getBlock().requiresTool || main.isCorrectToolForDrops(state); }
    void awardStat(Object stat) { stats++; }
    void causeFoodExhaustion(float amount) {}
    Vec3 getEyePosition(float partialTick) { return new Vec3(0.5, 2.62, 0.5); }
    Vec3 getViewVector(float partialTick) { return new Vec3(0, -1, 0); }
}
class ServerPlayer extends Player { ServerPlayer(Level level, ItemStack main) { super(level, main); } }
final class CompoundTag {
    final Map<String, Object> map = new TreeMap<>();
    void putInt(String key, int value) { map.put(key, value); }
    void putShort(String key, short value) { map.put(key, value); }
    void putString(String key, String value) { map.put(key, value); }
    void put(String key, CompoundTag value) { map.put(key, value); }
    int getInt(String key) { return map.get(key) instanceof Number n ? n.intValue() : 0; }
    short getShort(String key) { return map.get(key) instanceof Number n ? n.shortValue() : 0; }
    String getString(String key) { return map.get(key) instanceof String s ? s : ""; }
    CompoundTag getCompound(String key) { return map.get(key) instanceof CompoundTag t ? t : new CompoundTag(); }
    boolean contains(String key) { return map.containsKey(key); }
    void remove(String key) { map.remove(key); }
    boolean isEmpty() { return map.isEmpty(); }
    CompoundTag copy() { CompoundTag t = new CompoundTag(); map.forEach((k, v) -> t.map.put(k, v instanceof CompoundTag c ? c.copy() : v)); return t; }
    @Override public boolean equals(Object o) { return o instanceof CompoundTag t && map.equals(t.map); }
    @Override public int hashCode() { return map.hashCode(); }
    @Override public String toString() { return map.toString(); }
}
final class TagsUtil {
    static boolean hasCustomData(ItemStack stack) { return stack.customData != null; }
    static CompoundTag getCustomData(ItemStack stack) { return stack.customData == null ? new CompoundTag() : stack.customData.copy(); }
    static void putCustomData(ItemStack stack, CompoundTag tag) { stack.customData = tag.copy(); }
}
class ItemStack {
    static final ItemStack EMPTY = new ItemStack(null, 0);
    final Object item;
    int count, damage;
    final Map<String, Integer> enchantments = new TreeMap<>();
    CompoundTag customData;
    ItemStack(Object item) { this(item, 1); }
    ItemStack(Object item, int count) { this.item = item; this.count = count; }
    boolean isEmpty() { return item == null || count <= 0; }
    Object getItem() { return item; }
    int getCount() { return count; }
    void setCount(int count) { this.count = count; }
    int getMaxStackSize() { return 64; }
    void shrink(int amount) { count -= amount; }
    ItemStack copyWithCount(int count) { ItemStack s = copy(); s.count = count; return s; }
    // Item and data components; the stand-in compares the item and the custom data only.
    static boolean isSameItemSameComponents(ItemStack a, ItemStack b) { return a.item == b.item && Objects.equals(a.customData, b.customData); }
    ItemStack copy() {
        ItemStack s = new ItemStack(item, count);
        s.damage = damage;
        s.enchantments.putAll(enchantments);
        s.customData = customData == null ? null : customData.copy();
        return s;
    }
    boolean isDamageableItem() { return item != null; }
    int getMaxDamage() { return 100_000; }
    void hurtAndBreak(int amount, LivingEntity entity, EquipmentSlot slot) { damage += amount; }
    boolean isCorrectToolForDrops(BlockState state) { return item instanceof ToolAbilityItem tool && tool.isCorrectToolForDrops(this, state); }
    // ItemStack.mineBlock (contract-checked) delegates to Item.mineBlock.
    void mineBlock(Level level, BlockState state, BlockPos pos, Player player) { if(item instanceof Item i) i.mineBlock(this, level, state, pos, player); }
    @Override public String toString() { return count + "x" + item + enchantments + (customData == null ? "" : customData); }
}
final class Enchantment {}
final class Holder<T> { final String id; Holder(String id) { this.id = id; } }
final class Registries { static final String ENCHANTMENT = "minecraft:enchantment"; }
final class Enchantments { static final String SILK_TOUCH = "silk_touch"; static final String FORTUNE = "fortune"; }
final class Registry { <T> Holder<T> getHolderOrThrow(String key) { return new Holder<>(key); } }
final class RegistryAccess { Registry registryOrThrow(String key) { return new Registry(); } }
final class EnchantmentHelper {
    static final class Mutable {
        final ItemStack stack;
        Mutable(ItemStack stack) { this.stack = stack; }
        void set(Holder<Enchantment> holder, int level) { if(level <= 0) stack.enchantments.remove(holder.id); else stack.enchantments.put(holder.id, level); }
    }
    static void updateEnchantments(ItemStack stack, Consumer<Mutable> update) { update.accept(new Mutable(stack)); }
    static int getItemEnchantmentLevel(Holder<Enchantment> holder, ItemStack stack) { return stack.enchantments.getOrDefault(holder.id, 0); }
}
final class ConfigValue<T> { T value; ConfigValue(T value) { this.value = value; } T get() { return value; } void set(T value) { this.value = value; } }
final class NtmConfig {
    static final Common COMMON = new Common();
    static final Server SERVER = new Server();
    static final class Server { final ConfigValue<Boolean> CRATE_KEEP_CONTENTS = new ConfigValue<>(true); }
    static final class Common {
        final ConfigValue<Boolean> ABILITY_SILK = new ConfigValue<>(true), ABILITY_LUCK = new ConfigValue<>(true),
                ABILITY_VEIN = new ConfigValue<>(true), ABILITY_HAMMER = new ConfigValue<>(true),
                RECURSION_STONE = new ConfigValue<>(false), RECURSION_NETHERRACK = new ConfigValue<>(false);
        final ConfigValue<Integer> RECURSION_DEPTH = new ConfigValue<>(1000);
    }
}
final class RecipeType { static final RecipeType SMELTING = new RecipeType(); }
final class SingleRecipeInput { final ItemStack stack; SingleRecipeInput(ItemStack stack) { this.stack = stack; } }
final class SmeltingRecipe {
    final Object input; final ItemStack result;
    SmeltingRecipe(Object input, ItemStack result) { this.input = input; this.result = result; }
    boolean matches(SingleRecipeInput in, Level level) { return in.stack.item == input; }
    ItemStack getResultItem(RegistryAccess access) { return result; }
}
final class RecipeHolder { final SmeltingRecipe recipe; RecipeHolder(SmeltingRecipe recipe) { this.recipe = recipe; } SmeltingRecipe value() { return recipe; } }
final class RecipeManager { final List<RecipeHolder> smelting = new ArrayList<>(); List<RecipeHolder> getAllRecipesFor(RecipeType type) { return smelting; } }
final class ShredderRecipes {
    static final Map<Object, ItemStack> RECIPES = new HashMap<>();
    static boolean hasRecipe(ItemStack input) { return RECIPES.containsKey(input.item); }
    static ItemStack getShredderResult(ItemStack input) { ItemStack r = RECIPES.get(input.item); return r == null ? ItemStack.EMPTY : r.copy(); }
}
final class EventHooks { static boolean doPlayerHarvestCheck(Player player, BlockState state, Level level, BlockPos pos) { return player.hasCorrectToolForDrops(state); } }
interface IShearable { boolean isShearable(Player player, ItemStack stack, Level level, BlockPos pos); }
final class Stats { static final Stats BLOCK_MINED = new Stats(); Object get(Object block) { return block; } }
class HitResult { enum Type { MISS, BLOCK, ENTITY } final Type type; HitResult(Type type) { this.type = type; } Type getType() { return type; } }
class BlockHitResult extends HitResult { final Direction direction; BlockHitResult(Direction direction) { super(Type.BLOCK); this.direction = direction; } Direction getDirection() { return direction; } }
final class ClipContext {
    enum Block { COLLIDER }
    enum Fluid { NONE, ANY }
    ClipContext(Vec3 from, Vec3 to, Block block, Fluid fluid, Entity entity) {}
}
final class LootContextParam<T> { final String name; LootContextParam(String name) { this.name = name; } }
final class LootContextParams {
    static final LootContextParam<Vec3> ORIGIN = new LootContextParam<>("origin");
    static final LootContextParam<ItemStack> TOOL = new LootContextParam<>("tool");
    static final LootContextParam<Entity> THIS_ENTITY = new LootContextParam<>("this_entity");
    static final LootContextParam<BlockEntity> BLOCK_ENTITY = new LootContextParam<>("block_entity");
    static final LootContextParam<BlockState> BLOCK_STATE = new LootContextParam<>("block_state");
}
final class LootContextParamSets { static final String BLOCK = "block"; }
final class LootParams {
    final ServerLevel level; final Map<LootContextParam<?>, Object> params;
    LootParams(ServerLevel level, Map<LootContextParam<?>, Object> params) { this.level = level; this.params = params; }
    ServerLevel getLevel() { return level; }
    @SuppressWarnings("unchecked") <T> T getParameter(LootContextParam<T> key) {
        if(!params.containsKey(key)) throw new NoSuchElementException(key.name);
        return (T) params.get(key);
    }
    @SuppressWarnings("unchecked") <T> T getParamOrNull(LootContextParam<T> key) { return (T) params.get(key); }
    static final class Builder {
        final ServerLevel level; final Map<LootContextParam<?>, Object> params = new HashMap<>();
        Builder(ServerLevel level) { this.level = level; }
        <T> Builder withParameter(LootContextParam<T> key, T value) { params.put(key, value); return this; }
        <T> Builder withOptionalParameter(LootContextParam<T> key, T value) { if(value != null) params.put(key, value); return this; }
        LootParams create(String set) { return new LootParams(level, new HashMap<>(params)); }
    }
}
record Drop(BlockPos pos, ItemStack stack) {}
record AfterBreak(BlockPos pos, Block block, boolean inPlace, BlockEntity blockEntity, ItemStack tool) {}
class BlockEntity {
    final BlockPos pos; boolean removed; Level level;
    BlockEntity(BlockPos pos) { this.pos = pos; }
    boolean isRemoved() { return removed; }
    Level getLevel() { return level; }
}
interface EntityBlock { BlockEntity newBlockEntity(BlockPos pos, BlockState state); }
final class BlockState {
    final Block block;
    BlockState(Block block) { this.block = block; }
    Block getBlock() { return block; }
    boolean is(Block other) { return block == other; }
    boolean is(TagKey tag) { return block.tags.contains(tag); }
    boolean isAir() { return block.air; }
    boolean hasBlockEntity() { return block instanceof EntityBlock; }
    float getDestroyProgress(Player player, Level level, BlockPos pos) { return block.destroyProgress; }
    List<ItemStack> getDrops(LootParams.Builder builder) { return block.getDrops(this, builder); }
    // BlockStateBase.spawnAfterBreak (contract-checked) forwards to the block.
    void spawnAfterBreak(ServerLevel level, BlockPos pos, ItemStack stack, boolean dropExperience) { block.spawnAfterBreak(this, level, pos, stack, dropExperience); }
    void onRemove(Level level, BlockPos pos, BlockState newState, boolean moving) { block.onRemove(this, level, pos, newState, moving); }
    boolean canHarvestBlock(Level level, BlockPos pos, Player player) { return player.hasCorrectToolForDrops(this); }
    boolean onDestroyedByPlayer(Level level, BlockPos pos, Player player, boolean willHarvest) { return block.onDestroyedByPlayer(this, level, pos, player, willHarvest); }
    boolean canDropFromExplosion(Level level, BlockPos pos, Explosion explosion) { return block.canDropFromExplosion(this, level, pos, explosion); }
    void onBlockExploded(Level level, BlockPos pos, Explosion explosion) { block.onBlockExploded(this, level, pos, explosion); }
    // BlockStateBase.onExplosionHit forwards to BlockBehaviour.onExplosionHit (contract-checked), modeled for a DESTROY interaction
    // without an indirect player source (flag false).
    void onExplosionHit(Level level, BlockPos pos, Explosion explosion, BiConsumer<ItemStack, BlockPos> dropConsumer) {
        if(!isAir()) {
            if(canDropFromExplosion(level, pos, explosion) && level instanceof ServerLevel serverLevel) {
                BlockEntity blockEntity = hasBlockEntity() ? level.getBlockEntity(pos) : null;
                LootParams.Builder builder = new LootParams.Builder(serverLevel)
                        .withParameter(LootContextParams.ORIGIN, Vec3.atCenterOf(pos))
                        .withParameter(LootContextParams.TOOL, ItemStack.EMPTY)
                        .withOptionalParameter(LootContextParams.BLOCK_ENTITY, blockEntity)
                        .withOptionalParameter(LootContextParams.THIS_ENTITY, null);
                spawnAfterBreak(serverLevel, pos, ItemStack.EMPTY, false);
                getDrops(builder).forEach(stack -> dropConsumer.accept(stack, pos));
            }
            onBlockExploded(level, pos, explosion);
        }
    }
    @Override public String toString() { return block.toString(); }
}
class Block {
    final String name;
    final BlockState defaultState = new BlockState(this);
    final Set<TagKey> tags = new HashSet<>();
    boolean air, requiresTool = true;
    float destroyProgress = 0.05F;
    Block(String name) { this.name = name; }
    Block mineable() { tags.add(BlockTags.MINEABLE_WITH_PICKAXE); return this; }
    BlockState defaultBlockState() { return defaultState; }
    Object asItem() { return this; }
    @Override public String toString() { return name; }
    // BlockBehaviour defaults. spawnAfterBreak is a no-op in the game; here it records the call and what is still in place.
    protected List<ItemStack> getDrops(BlockState state, LootParams.Builder params) { return new ArrayList<>(List.of(new ItemStack(this))); }
    protected void spawnAfterBreak(BlockState state, ServerLevel level, BlockPos pos, ItemStack tool, boolean dropExperience) {
        level.afterBreak.add(new AfterBreak(pos, this, level.getBlockState(pos).is(this), level.getBlockEntity(pos), tool));
    }
    // IBlockExtension.canDropFromExplosion / onBlockExploded defaults (contract-checked); wasExploded does nothing for the blocks involved.
    boolean canDropFromExplosion(BlockState state, Level level, BlockPos pos, Explosion explosion) { return true; }
    public void onBlockExploded(BlockState state, Level level, BlockPos pos, Explosion explosion) { level.setBlock(pos, Blocks.AIR.defaultBlockState(), 3); }
    protected void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean movedByPiston) {
        if(state.hasBlockEntity() && !state.is(newState.getBlock())) level.removeBlockEntity(pos);
    }
    BlockState playerWillDestroy(Level level, BlockPos pos, BlockState state, Player player) { return state; }
    // IBlockExtension.onDestroyedByPlayer default (contract-checked): the server calls Level.removeBlock(pos, false).
    boolean onDestroyedByPlayer(BlockState state, Level level, BlockPos pos, Player player, boolean willHarvest) { return level.removeBlock(pos, false); }
    void destroy(Level level, BlockPos pos, BlockState state) {}
    // Block.playerDestroy (contract-checked).
    public void playerDestroy(Level level, Player player, BlockPos pos, BlockState state, @Nullable BlockEntity blockEntity, ItemStack tool) {
        player.awardStat(Stats.BLOCK_MINED.get(this));
        player.causeFoodExhaustion(0.005F);
        dropResources(state, level, pos, blockEntity, player, tool);
    }
    // Block.getDrops(state, level, pos, blockEntity, entity, tool) (contract-checked).
    static List<ItemStack> getDrops(BlockState state, ServerLevel level, BlockPos pos, @Nullable BlockEntity blockEntity, @Nullable Entity entity, ItemStack tool) {
        LootParams.Builder builder = new LootParams.Builder(level)
                .withParameter(LootContextParams.ORIGIN, Vec3.atCenterOf(pos))
                .withParameter(LootContextParams.TOOL, tool)
                .withOptionalParameter(LootContextParams.THIS_ENTITY, entity)
                .withOptionalParameter(LootContextParams.BLOCK_ENTITY, blockEntity);
        return state.getDrops(builder);
    }
    // Block.dropResources -> CommonHooks.handleBlockDrops with an uncancelled BlockDropsEvent (contract-checked).
    static void dropResources(BlockState state, Level level, BlockPos pos, @Nullable BlockEntity blockEntity, @Nullable Entity entity, ItemStack tool) {
        if(level instanceof ServerLevel serverLevel) {
            getDrops(state, serverLevel, pos, blockEntity, entity, tool).forEach(stack -> popResource(level, pos, stack));
            state.spawnAfterBreak(serverLevel, pos, tool, false);
        }
    }
    static void popResource(Level level, BlockPos pos, ItemStack stack) { if(!level.isClientSide && !stack.isEmpty()) level.drops.add(new Drop(pos, stack.copy())); }
}
final class Blocks {
    static final Block AIR = air();
    static final Block STONE = new Block("stone").mineable();
    static final Block NETHERRACK = new Block("netherrack").mineable();
    private static Block air() { Block b = new Block("air"); b.air = true; b.requiresTool = false; return b; }
}
abstract class BaseEntityBlock extends Block implements EntityBlock { BaseEntityBlock(String name) { super(name); mineable(); } }
class DummyableBlock extends Block { DummyableBlock(String name) { super(name); } BlockPos findCore(Level level, BlockPos pos) { return null; } }
class Level {
    boolean isClientSide;
    final Map<BlockPos, BlockState> states = new HashMap<>();
    final Map<BlockPos, BlockEntity> blockEntities = new HashMap<>();
    final List<Drop> drops = new ArrayList<>();
    final List<AfterBreak> afterBreak = new ArrayList<>();
    int slotDrops;
    final RecipeManager recipes = new RecipeManager();
    final RegistryAccess registries = new RegistryAccess();
    HitResult clipResult = new HitResult(HitResult.Type.MISS);
    BlockState getBlockState(BlockPos pos) { return states.getOrDefault(pos, Blocks.AIR.defaultBlockState()); }
    BlockEntity getBlockEntity(BlockPos pos) { return blockEntities.get(pos); }
    void removeBlockEntity(BlockPos pos) { BlockEntity be = blockEntities.remove(pos); if(be != null) be.removed = true; }
    RegistryAccess registryAccess() { return registries; }
    RecipeManager getRecipeManager() { return recipes; }
    HitResult clip(ClipContext context) { return clipResult; }
    // Level.setBlock -> LevelChunk.setBlockState (contract-checked): an unchanged state returns false; otherwise the new state
    // is stored first and the server then calls the old state's onRemove while its block entity is still registered.
    boolean setBlock(BlockPos pos, BlockState state, int flags) {
        BlockState old = getBlockState(pos);
        if(old == state) return false;
        if(state.isAir()) states.remove(pos); else states.put(pos, state);
        if(!isClientSide) old.onRemove(this, pos, state, (flags & 64) != 0);
        return true;
    }
    // Level.removeBlock (contract-checked).
    boolean removeBlock(BlockPos pos, boolean isMoving) { return setBlock(pos, Blocks.AIR.defaultBlockState(), 3 | (isMoving ? 64 : 0)); }
    // LevelAccessor.destroyBlock(pos, dropBlock) -> Level.destroyBlock (contract-checked): no entity, an empty tool, no fluid; the
    // loot pass (Block.dropResources) runs before the block is replaced.
    boolean destroyBlock(BlockPos pos, boolean dropBlock) {
        BlockState state = getBlockState(pos);
        if(state.isAir()) return false;
        if(dropBlock) {
            BlockEntity blockEntity = state.hasBlockEntity() ? getBlockEntity(pos) : null;
            Block.dropResources(state, this, pos, blockEntity, null, ItemStack.EMPTY);
        }
        return setBlock(pos, Blocks.AIR.defaultBlockState(), 3);
    }
}
class ServerLevel extends Level {}
final class Containers {
    static void dropContents(Level level, BlockPos pos, BarrelBlockEntity barrel) { level.slotDrops += barrel.inventory; barrel.inventory = 0; }
    // Containers.dropContents -> dropItemStack (contract-checked): each slot stack leaves at the block's position and is split down to
    // empty. The game spawns several item entities per stack; one Drop of the whole stack stands for them.
    static void dropContents(Level level, BlockPos pos, CrateBaseBlockEntity crate) {
        for(ItemStack stack : crate.slots) {
            if(stack.isEmpty()) continue;
            level.drops.add(new Drop(pos, stack.copy()));
            stack.setCount(0);
        }
    }
}
// Explosion.finalizeExplosion's block part (contract-checked). The game shuffles toBlow; the caller supplies the order instead.
final class Explosion {
    final ServerLevel level; final List<BlockPos> toBlow;
    Explosion(ServerLevel level, List<BlockPos> toBlow) { this.level = level; this.toBlow = toBlow; }
    void finalizeExplosion() {
        List<Drop> list = new ArrayList<>();
        for(BlockPos pos : toBlow) level.getBlockState(pos).onExplosionHit(level, pos, this, (stack, at) -> addOrAppendStack(list, stack, at));
        for(Drop pair : list) Block.popResource(level, pair.pos(), pair.stack());
    }
    // addOrAppendStack with ItemEntity.areMergable / merge(stack, stack, 16) (contract-checked): a mergeable stack joins the first
    // matching pair, so equal crate items collected from different crates are popped together at the first crate's position.
    private static void addOrAppendStack(List<Drop> drops, ItemStack stack, BlockPos pos) {
        for(int i = 0; i < drops.size(); i++) {
            Drop pair = drops.get(i);
            ItemStack itemstack = pair.stack();
            if(stack.getCount() + itemstack.getCount() <= stack.getMaxStackSize() && ItemStack.isSameItemSameComponents(itemstack, stack)) {
                int moved = Math.min(Math.min(itemstack.getMaxStackSize(), 16) - itemstack.getCount(), stack.getCount());
                drops.set(i, new Drop(pair.pos(), itemstack.copyWithCount(itemstack.getCount() + moved)));
                stack.shrink(moved);
                if(stack.isEmpty()) return;
            }
        }
        drops.add(new Drop(pos, stack));
    }
}
final class FluidTank {
    String type; int fill; final int max;
    FluidTank(String type, int max) { this.type = type; this.max = max; }
    int getFill() { return fill; }
    void writeToNBT(CompoundTag tag, String s) { tag.putInt(s, fill); tag.putInt(s + "_max", max); tag.putString(s + "_type", type); }
    void readFromNBT(CompoundTag tag, String s) { fill = tag.getInt(s); type = tag.getString(s + "_type"); }
}
class Item { public boolean mineBlock(ItemStack stack, Level level, BlockState state, BlockPos pos, LivingEntity miningEntity) { return false; } }
final class Tier { float getSpeed() { return 8.0F; } }
class TieredItem extends Item { final Tier tier = new Tier(); Tier getTier() { return tier; } }
final class ToolPreset {
    final IToolAreaAbility areaAbility; final int areaAbilityLevel;
    final IToolHarvestAbility harvestAbility; final int harvestAbilityLevel;
    ToolPreset(IToolAreaAbility area, int areaLevel, IToolHarvestAbility harvest, int harvestLevel) {
        this.areaAbility = area; this.areaAbilityLevel = areaLevel; this.harvestAbility = harvest; this.harvestAbilityLevel = harvestLevel;
    }
}
final class Configuration { final ToolPreset preset; Configuration(ToolPreset preset) { this.preset = preset; } ToolPreset getActivePreset() { return preset; } }
interface IBaseAbility extends Comparable<IBaseAbility> {
    String getName();
    default String getExtension(int level) { return ""; }
    default boolean isAllowed() { return true; }
    default int levels() { return 1; }
    default int sortOrder() { return hashCode(); }
    @Override default int compareTo(IBaseAbility ability) { return sortOrder() - ability.sortOrder(); }
}
interface IToolHarvestAbility extends IBaseAbility {
__HARVEST__
}
interface IToolAreaAbility extends IBaseAbility {
__AREA__
}
class ToolAbilityItem extends TieredItem {
    enum ToolRole { PICKAXE, AXE, SHOVEL, HOE, MINER }
    private final ToolRole toolRole = ToolRole.PICKAXE;
    private boolean isShears;
    Configuration config;
    // The real getConfiguration reads the preset list from the stack's custom data.
    Configuration getConfiguration(ItemStack stack) { return config; }
__TOOL__
}
interface IPersistentNBT {
__PERSISTENT__
}
final class CompatExternal {
__COMPAT__
}
class BarrelBlockEntity extends BlockEntity implements IPersistentNBT {
    public final FluidTank tank;
    public short mode = 0;
    private boolean shouldDrop = true;
    int inventory;
    BarrelBlockEntity(BlockPos pos, BlockState state) {
        super(pos);
        this.tank = new FluidTank("NONE", state.getBlock() instanceof BarrelBlock barrel ? barrel.getCapacity() : 12_000);
    }
__BARREL_BE__
}
class BarrelBlock extends BaseEntityBlock {
    private final int capacity;
    private final boolean corroded;
    BarrelBlock(String name, int capacity, boolean corroded) { super(name); this.capacity = capacity; this.corroded = corroded; }
    int getCapacity() { return this.capacity; }
    boolean isCorroded() { return this.corroded; }
__BARREL__
}
class CrateBaseBlockEntity extends BlockEntity implements IPersistentNBT {
    final List<ItemStack> slots = new ArrayList<>();
    private boolean shouldDrop = true;
    CrateBaseBlockEntity(BlockPos pos, int size) { super(pos); for(int i = 0; i < size; i++) slots.add(ItemStack.EMPTY); }
    // The real saveAdditional writes "Items" (slot index and ItemStack.save), "Spiders" and "Name"; this keeps what identifies the slots.
    void saveAdditional(CompoundTag tag, RegistryAccess registries) {
        CompoundTag items = new CompoundTag();
        for(int i = 0; i < slots.size(); i++) {
            ItemStack stack = slots.get(i);
            if(stack.isEmpty()) continue;
            CompoundTag itemTag = new CompoundTag();
            itemTag.putInt("Slot", i);
            itemTag.putString("id", String.valueOf(stack.item));
            itemTag.putInt("count", stack.count);
            if(stack.customData != null) itemTag.put("components", stack.customData.copy());
            items.put("slot" + i, itemTag);
        }
        tag.put("Items", items);
    }
    // Restoring a placed crate is not on any break path.
    public void readNBT(CompoundTag savedTag) {}
__CRATE_BE__
}
class CrateBlock extends BaseEntityBlock {
    enum Type { IRON(36), STEEL(54); final int slots; Type(int slots) { this.slots = slots; } }
    private final Type type;
    CrateBlock(String name, Type type) { super(name); this.type = type; }
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) { return new CrateBaseBlockEntity(pos, type.slots); }
__CRATE__
}
'''


def build_world(source: Path):
    text = {path: (source / path).read_text(encoding="utf-8") for path in PRODUCTION}
    harvest = region(text[HARVEST], "    default void preHarvestAll(", "    // endregion handlers")
    area_text = text[AREA]
    area = "\n".join([region(area_text, "    // Should call tool.breakExtraBlock", "    int SORT_ORDER_BASE = 0;")]
                     + [declaration(area_text, f"    IToolAreaAbility {name} = new IToolAreaAbility()") for name in AREA_HANDLERS])
    persistent = region(text[PERSISTENT], "    String NBT_PERSISTENT_KEY", "        return new ArrayList<>();\n    }")
    return (STUBS.replace("__HARVEST__", harvest)
            .replace("__AREA__", area)
            .replace("__TOOL__", "\n".join("    " + method(text[TOOL], s) for s in TOOL_METHODS))
            .replace("__PERSISTENT__", persistent)
            .replace("__COMPAT__", "    " + method(text[COMPAT], "public static BlockEntity getCoreFromPos("))
            .replace("__BARREL_BE__", "\n".join("    " + method(text[BARREL_BE], s) for s in BARREL_BE_METHODS))
            .replace("__BARREL__", "\n".join("    " + method(text[BARREL], s) for s in BARREL_METHODS))
            .replace("__CRATE_BE__", "\n".join("    " + method(text[CRATE_BE], s) for s in CRATE_BE_METHODS))
            .replace("__CRATE__", "\n".join("    " + method(text[CRATE], s) for s in CRATE_METHODS)))
