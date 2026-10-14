"""Bounded method-level world for the tool-ability harvest fix and the drops batch.

The production harvest path is copied verbatim into compile shells: the harvest
handlers of IToolHarvestAbility, the mining entry points of ToolAbilityItem (including
breakExtraBlock's BreakEvent and isMinedStructure), the vein/hammer/explosion area
handlers of IToolAreaAbility, the barrel and crate block and block-entity drop methods,
IPersistentNBT, CompatExternal.getCoreFromPos, the DummyableBlock core search, removal
cascade and drop methods, MachineRefineryBlock's block entities and persistent loot,
MachineCentrifugeBlock's footprint clearing, OutgasBlock.spawnAfterBreak and the whole
BlockProcessorStandard class. Minecraft and NeoForge block breaking
(ServerPlayerGameMode.destroyBlock, CommonHooks.fireBlockBreak, Level.setBlock with
its neighbor notification through CollectingNeighborUpdater, Level.destroyBlock,
LevelChunk.setBlockState, BlockBehaviour.onRemove, Block.getDrops/dropResources, the
vanilla explosion drop pass, InfestedBlock.spawnAfterBreak) is modeled below and in
AbilityHarvestRegression.java; the verifier checks that order against the cached
NeoForge sources and ExplosionVNT.explode against the NEO source. Loot, NBT,
enchantment, recipe, config, block-entity data and the explosion ray allocator are
minimal stand-ins. This is not a Minecraft launch or a whole-class compilation; the real
APIs are checked by the main build.
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
DUMMYABLE = "com/hbm/blocks/DummyableBlock.java"
REFINERY = "com/hbm/blocks/machine/MachineRefineryBlock.java"
CENTRIFUGE = "com/hbm/blocks/machine/MachineCentrifugeBlock.java"
PROCESSOR = "com/hbm/explosion/vanillant/standard/BlockProcessorStandard.java"
OUTGAS = "com/hbm/blocks/generic/OutgasBlock.java"
VNT = "com/hbm/explosion/vanillant/ExplosionVNT.java"
PRODUCTION = (HARVEST, AREA, TOOL, BARREL, BARREL_BE, CRATE, CRATE_BE, PERSISTENT, COMPAT,
              DUMMYABLE, REFINERY, CENTRIFUGE, PROCESSOR, OUTGAS, VNT)

TOOL_METHODS = (
    "public boolean mineBlock(", "public float getDestroySpeed(", "public boolean isCorrectToolForDrops(ItemStack",
    "private boolean isEffectiveForState(", "public static boolean canTakeDamage(", "public static void damageTool(",
    "public boolean canOperate(", "public boolean canHarvest(", "public boolean canShearBlock(",
    "public boolean isShears(", "public void breakExtraBlock(", "public static boolean isMinedStructure(",
)
DUMMYABLE_FIELDS = (
    "    public static final DirectionProperty FACING = DirectionProperty.create(\"facing\", Direction.values());\n",
    "    public static final EnumProperty<DummyBlockType> TYPE = EnumProperty.create(\"type\", DummyBlockType.class);\n",
    "    public static boolean safeRem = false;\n",
    "    private final List<BlockPos> positions = new ArrayList<>();\n",
)
DUMMYABLE_METHODS = (
    "public BlockState createDummyState(", "public BlockState createExtraState(", "public BlockState createCoreState(",
    "public static boolean isCore(", "public static Direction getPointingDirection(", "public void neighborChanged(",
    "private void destroyIfOrphan(", "public BlockPos findCore(", "private BlockPos findCoreRecursive(",
    "public void onRemove(", "public void playerDestroy(", "public BlockState playerWillDestroy(",
)
REFINERY_METHODS = ("public BlockEntity newBlockEntity(", "protected List<ItemStack> getDrops(")
CENTRIFUGE_METHODS = (
    "public BlockEntity newBlockEntity(", "public BlockState playerWillDestroy(", "public void onRemove(",
    "private void destroyCentrifuge(", "private BlockPos findOwnedCore(",
)
BARREL_METHODS = (
    "public BlockEntity newBlockEntity(", "public void onRemove(", "public void playerDestroy(",
    "protected void spawnAfterBreak(", "protected List<ItemStack> getDrops(", "public void onBlockExploded(",
)
BARREL_BE_METHODS = ("public void writeNBT(", "public void readNBT(", "public boolean shouldDrop(", "public void preventDrop(")
CRATE_METHODS = ("public void onRemove(", "public void playerDestroy(", "protected void spawnAfterBreak(", "protected List<ItemStack> getDrops(")
CRATE_BE_METHODS = ("public void writeNBT(", "public boolean shouldDrop(", "public void preventDrop(")
AREA_HANDLERS = ("NONE", "RECURSION", "HAMMER", "HAMMER_FLAT", "EXPLOSION")

STUBS = r'''package abilityharvest;
import java.util.*;
import java.util.function.*;
@interface Nullable {}
record BlockPos(int x, int y, int z) {
    int getX() { return x; }
    int getY() { return y; }
    int getZ() { return z; }
    BlockPos offset(BlockPos o) { return new BlockPos(x + o.x, y + o.y, z + o.z); }
    BlockPos offset(int dx, int dy, int dz) { return new BlockPos(x + dx, y + dy, z + dz); }
    BlockPos relative(Direction d) { return relative(d, 1); }
    BlockPos relative(Direction d, int n) { return new BlockPos(x + d.stepX * n, y + d.stepY * n, z + d.stepZ * n); }
    BlockPos above() { return above(1); }
    BlockPos above(int n) { return new BlockPos(x, y + n, z); }
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
enum Direction {
    DOWN(0, -1, 0), UP(0, 1, 0), NORTH(0, 0, -1), SOUTH(0, 0, 1), WEST(-1, 0, 0), EAST(1, 0, 0);
    final int stepX, stepY, stepZ;
    Direction(int x, int y, int z) { stepX = x; stepY = y; stepZ = z; }
    int getStepX() { return stepX; }
    int getStepZ() { return stepZ; }
    Direction getOpposite() {
        return switch(this) { case DOWN -> UP; case UP -> DOWN; case NORTH -> SOUTH; case SOUTH -> NORTH; case WEST -> EAST; case EAST -> WEST; };
    }
}
// Block-state properties with interned states (see Block.stateFor), so Level.setBlock's identity check still models LevelChunk's.
class Property<T> { final String name; Property(String name) { this.name = name; } @Override public String toString() { return name; } }
final class DirectionProperty extends Property<Direction> {
    DirectionProperty(String name) { super(name); }
    static DirectionProperty create(String name, Direction... values) { return new DirectionProperty(name); }
}
final class EnumProperty<E extends Enum<E>> extends Property<E> {
    EnumProperty(String name) { super(name); }
    static <E extends Enum<E>> EnumProperty<E> create(String name, Class<E> type) { return new EnumProperty<>(name); }
}
// com.hbm.blocks.DummyBlockType without its serialized names.
enum DummyBlockType { DUMMY, EXTRA, CORE }
// Stands in for java.util.Collections inside this package so RECURSION's Collections.shuffle is reproducible per seed.
final class Collections {
    static Random random = new Random(0);
    static void shuffle(List<?> list) { java.util.Collections.shuffle(list, random); }
}
// One ordered record of every world mutation, drop, spawnAfterBreak, BreakEvent and tool damage, for order checks.
record Step(String kind, BlockPos pos, Object detail) {}
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
    // Abilities as GameType.updatePlayerAbilities sets them: instabuild in creative, mayBuild outside adventure and spectator.
    boolean instabuild, mayBuild = true;
    boolean hasInfiniteMaterials() { return instabuild; }
    boolean mayBuild() { return mayBuild; }
    boolean canUseGameMasterBlocks() { return false; }
    // Player.blockActionRestricted (contract-checked).
    boolean blockActionRestricted(Level level, BlockPos pos, GameType gameMode) {
        if (!gameMode.isBlockPlacingRestricted()) {
            return false;
        } else if (gameMode == GameType.SPECTATOR) {
            return true;
        } else if (this.mayBuild()) {
            return false;
        } else {
            ItemStack itemstack = this.getMainHandItem();
            return itemstack.isEmpty() || !itemstack.canBreakBlockInAdventureMode(level.getBlockState(pos));
        }
    }
}
enum GameType {
    SURVIVAL, CREATIVE, ADVENTURE, SPECTATOR;
    boolean isCreative() { return this == CREATIVE; }
    boolean isBlockPlacingRestricted() { return this == ADVENTURE || this == SPECTATOR; }
}
final class ServerPlayerGameMode {
    GameType gameModeForPlayer = GameType.SURVIVAL;
    GameType getGameModeForPlayer() { return gameModeForPlayer; }
    boolean isCreative() { return gameModeForPlayer.isCreative(); }
}
record BlockUpdatePacket(BlockPos pos, BlockState state) {}
final class Connection { final List<BlockUpdatePacket> sent = new ArrayList<>(); void send(BlockUpdatePacket packet) { sent.add(packet); } }
class ServerPlayer extends Player {
    final ServerPlayerGameMode gameMode = new ServerPlayerGameMode();
    final Connection connection = new Connection();
    ServerPlayer(Level level, ItemStack main) { super(level, main); }
    void setGameMode(GameType type) { gameMode.gameModeForPlayer = type; instabuild = type.isCreative(); mayBuild = !type.isBlockPlacingRestricted(); }
}
interface GameMasterBlock {}
// BlockEvent.BreakEvent: the event fireBlockBreak posts for one block.
final class BreakEvent {
    final Level level; final BlockPos pos; final BlockState state; final Player player;
    private boolean canceled;
    BreakEvent(Level level, BlockPos pos, BlockState state, Player player) { this.level = level; this.pos = pos; this.state = state; this.player = player; }
    boolean isCanceled() { return canceled; }
    void setCanceled(boolean canceled) { this.canceled = canceled; }
    BlockPos getPos() { return pos; }
}
final class EventBus { final List<Consumer<BreakEvent>> listeners = new ArrayList<>(); void post(BreakEvent event) { for(Consumer<BreakEvent> l : listeners) l.accept(event); } }
final class NeoForge { static final EventBus EVENT_BUS = new EventBus(); }
// What fireBlockBreak was given and decided, for the regression; the real event does not carry the game type.
record BreakRecord(BreakEvent event, GameType gameType, boolean preCanceled) {}
final class CommonHooks {
    // CommonHooks.fireBlockBreak (contract-checked): pre-cancel for an item that cannot attack the block, a restricted block action or
    // a game-master block, post on the event bus, and resend the block to the client when cancelled.
    static BreakEvent fireBlockBreak(Level level, GameType gameType, ServerPlayer player, BlockPos pos, BlockState state) {
        boolean preCancelEvent = false;
        ItemStack itemstack = player.getMainHandItem();
        if (!itemstack.isEmpty() && itemstack.getItem() instanceof Item item && !item.canAttackBlock(state, level, pos, player)) {
            preCancelEvent = true;
        }
        if (player.blockActionRestricted(level, pos, gameType)) {
            preCancelEvent = true;
        }
        if (state.getBlock() instanceof GameMasterBlock && !player.canUseGameMasterBlocks()) {
            preCancelEvent = true;
        }
        BreakEvent event = new BreakEvent(level, pos, state, player);
        event.setCanceled(preCancelEvent);
        level.journal.add(new Step("event", pos, event));
        NeoForge.EVENT_BUS.post(event);
        level.breakEvents.add(new BreakRecord(event, gameType, preCancelEvent));
        if (event.isCanceled()) {
            player.connection.send(new BlockUpdatePacket(pos, state));
        }
        return event;
    }
}
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
    // The CAN_BREAK adventure-mode predicate, reduced to the blocks it names.
    final Set<Block> canBreak = new HashSet<>();
    boolean canBreakBlockInAdventureMode(BlockState state) { return canBreak.contains(state.getBlock()); }
    void enchant(Holder<Enchantment> holder, int level) { enchantments.put(holder.id, level); }
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
    // ItemStack.hurtAndBreak (contract-checked): a holder with infinite materials takes no wear. The call is journaled either way.
    void hurtAndBreak(int amount, LivingEntity entity, EquipmentSlot slot) {
        if(!(entity instanceof Player holder && holder.hasInfiniteMaterials())) damage += amount;
        if(entity instanceof Player player) player.level.journal.add(new Step("damage", null, amount));
    }
    boolean isCorrectToolForDrops(BlockState state) { return item instanceof ToolAbilityItem tool && tool.isCorrectToolForDrops(this, state); }
    // ItemStack.mineBlock (contract-checked) delegates to Item.mineBlock.
    void mineBlock(Level level, BlockState state, BlockPos pos, Player player) { if(item instanceof Item i) i.mineBlock(this, level, state, pos, player); }
    @Override public String toString() { return count + "x" + item + enchantments + (customData == null ? "" : customData); }
}
final class Enchantment {}
final class Items { static final Object DIAMOND_PICKAXE = "diamond_pickaxe"; }
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
                ABILITY_VEIN = new ConfigValue<>(true), ABILITY_HAMMER = new ConfigValue<>(true), ABILITY_EXPLOSION = new ConfigValue<>(true),
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
// Every BlockState.spawnAfterBreak call, including blocks that do not call super (OutgasBlock).
record AfterBreakCall(BlockPos pos, BlockState state, boolean inPlace, ItemStack tool, boolean dropExperience) {}
class BlockEntity {
    final BlockPos pos; boolean removed; Level level;
    BlockEntity(BlockPos pos) { this.pos = pos; }
    boolean isRemoved() { return removed; }
    Level getLevel() { return level; }
}
interface EntityBlock { BlockEntity newBlockEntity(BlockPos pos, BlockState state); }
final class BlockState {
    final Block block;
    final Map<Property<?>, Object> values;
    BlockState(Block block, Map<Property<?>, Object> values) { this.block = block; this.values = values; }
    Block getBlock() { return block; }
    @SuppressWarnings("unchecked") <T> T getValue(Property<T> property) {
        if(!values.containsKey(property)) throw new IllegalArgumentException("no " + property + " on " + this);
        return (T) values.get(property);
    }
    <T> BlockState setValue(Property<T> property, T value) {
        Map<Property<?>, Object> next = new HashMap<>(values);
        next.put(property, value);
        return block.stateFor(next);
    }
    // BlockStateBase.handleNeighborChanged (contract-checked) forwards to the block.
    void handleNeighborChanged(Level level, BlockPos pos, Block neighborBlock, BlockPos neighborPos, boolean movedByPiston) {
        block.neighborChanged(this, level, pos, neighborBlock, neighborPos, movedByPiston);
    }
    boolean is(Block other) { return block == other; }
    boolean is(TagKey tag) { return block.tags.contains(tag); }
    boolean isAir() { return block.air; }
    boolean hasBlockEntity() { return block instanceof EntityBlock; }
    float getDestroyProgress(Player player, Level level, BlockPos pos) { return block.destroyProgress; }
    List<ItemStack> getDrops(LootParams.Builder builder) { return block.getDrops(this, builder); }
    // BlockStateBase.spawnAfterBreak (contract-checked) forwards to the block. The call is recorded here, before the block runs it.
    void spawnAfterBreak(ServerLevel level, BlockPos pos, ItemStack stack, boolean dropExperience) {
        AfterBreakCall call = new AfterBreakCall(pos, this, level.getBlockState(pos) == this, stack, dropExperience);
        level.afterBreakCalls.add(call);
        level.journal.add(new Step("after", pos, call));
        block.spawnAfterBreak(this, level, pos, stack, dropExperience);
    }
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
    @Override public String toString() { return values.isEmpty() ? block.toString() : block + "" + values; }
}
class Block {
    final String name;
    private final Map<Map<Property<?>, Object>, BlockState> states = new HashMap<>();
    private BlockState defaultState = stateFor(Map.of());
    final Set<TagKey> tags = new HashSet<>();
    boolean air, requiresTool = true;
    float destroyProgress = 0.05F;
    Block(String name) { this.name = name; }
    Block mineable() { tags.add(BlockTags.MINEABLE_WITH_PICKAXE); return this; }
    BlockState defaultBlockState() { return defaultState; }
    // One interned state per property map, as the game's StateDefinition holds.
    BlockState stateFor(Map<Property<?>, Object> values) { return states.computeIfAbsent(Map.copyOf(values), v -> new BlockState(this, v)); }
    void registerDefaultState(BlockState state) { defaultState = state; }
    // BlockBehaviour.neighborChanged default (contract-checked) only sends a debug packet.
    protected void neighborChanged(BlockState state, Level level, BlockPos pos, Block neighborBlock, BlockPos neighborPos, boolean movedByPiston) {}
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
    static void popResource(Level level, BlockPos pos, ItemStack stack) {
        if(!level.isClientSide && !stack.isEmpty()) {
            Drop drop = new Drop(pos, stack.copy());
            level.drops.add(drop);
            level.journal.add(new Step("drop", pos, drop));
        }
    }
}
final class Blocks {
    static final Block AIR = air();
    static final Block STONE = new Block("stone").mineable();
    static final Block NETHERRACK = new Block("netherrack").mineable();
    // Air has no loot (an air item stack is empty in the game).
    private static Block air() {
        Block b = new Block("air") { @Override protected List<ItemStack> getDrops(BlockState state, LootParams.Builder params) { return new ArrayList<>(); } };
        b.air = true; b.requiresTool = false; return b;
    }
}
abstract class BaseEntityBlock extends Block implements EntityBlock { BaseEntityBlock(String name) { super(name); mineable(); } }
interface BlockGetter { BlockState getBlockState(BlockPos pos); }
abstract class DummyableBlock extends BaseEntityBlock {
__DUMMYABLE_FIELDS__
    // As the real constructor: the default state is a NORTH-facing core.
    DummyableBlock(String name) {
        super(name);
        registerDefaultState(defaultBlockState().setValue(FACING, Direction.NORTH).setValue(TYPE, DummyBlockType.CORE));
    }
__DUMMYABLE__
}
// MachineRefineryBlock: its block entities per part type and its persistent loot.
class MachineRefineryBlock extends DummyableBlock {
    MachineRefineryBlock(String name) { super(name); }
__REFINERY__
}
// MachineCentrifugeBlock: clears its whole column when any part is broken or removed. Its loot is the default (one plain body).
class MachineCentrifugeBlock extends DummyableBlock {
    MachineCentrifugeBlock(String name) { super(name); }
__CENTRIFUGE__
}
// Stand-in for the refinery core: the real one saves five tanks; this keeps a string that tells two refineries apart.
class MachineRefineryBlockEntity extends BlockEntity implements IPersistentNBT {
    String tanks = "";
    MachineRefineryBlockEntity(BlockPos pos, BlockState state) { super(pos); }
    public void writeNBT(CompoundTag savedTag) { CompoundTag data = new CompoundTag(); data.putString("tanks", tanks); savedTag.put(NBT_PERSISTENT_KEY, data); }
    public void readNBT(CompoundTag savedTag) {}
}
class MachineCentrifugeBlockEntity extends BlockEntity { MachineCentrifugeBlockEntity(BlockPos pos, BlockState state) { super(pos); } }
// Stand-in proxy: not persistent and, unlike the real WorldlyContainer proxy, not a Container (slot contents are not modeled).
class ProxyComboBlockEntity extends BlockEntity {
    ProxyComboBlockEntity(BlockPos pos, BlockState state) { super(pos); }
    ProxyComboBlockEntity inventory() { return this; }
    ProxyComboBlockEntity power() { return this; }
    ProxyComboBlockEntity fluid() { return this; }
}
// OutgasBlock with its spawnAfterBreak; getGas is the stand-in for the NtmBlocks lookup (the asbestos brick's gas).
class OutgasBlock extends Block {
    private final boolean onBreak;
    private final Block gas;
    OutgasBlock(String name, boolean onBreak, Block gas) { super(name); mineable(); this.onBreak = onBreak; this.gas = gas; }
    BlockState getGas() { return gas.defaultBlockState(); }
__OUTGAS__
}
// InfestedBlock.spawnAfterBreak (contract-checked): with block drops on and a tool without silk touch (the enchantment tag that prevents
// infested spawns) it spawns a silverfish, counted here. The loot is a stand-in for the infested-stone table: the host block with silk
// touch, otherwise nothing.
final class InfestedBlock extends Block {
    final Block host;
    InfestedBlock(String name, Block host) { super(name); mineable(); this.host = host; }
    @Override protected void spawnAfterBreak(BlockState state, ServerLevel level, BlockPos pos, ItemStack stack, boolean dropExperience) {
        super.spawnAfterBreak(state, level, pos, stack, dropExperience);
        if (level.doBlockDrops && !stack.enchantments.containsKey(Enchantments.SILK_TOUCH)) {
            level.silverfish++;
        }
    }
    @Override protected List<ItemStack> getDrops(BlockState state, LootParams.Builder params) {
        ItemStack tool = params.withParameter(LootContextParams.BLOCK_STATE, state).create(LootContextParamSets.BLOCK).getParamOrNull(LootContextParams.TOOL);
        return tool != null && tool.enchantments.containsKey(Enchantments.SILK_TOUCH) ? new ArrayList<>(List.of(new ItemStack(host))) : new ArrayList<>();
    }
}
// CollectingNeighborUpdater (contract-checked) with only the MultiNeighborUpdate that Level.setBlock queues: the first update runs at
// once; updates queued while it runs go to addedThisLayer and run depth-first before the rest of the current one, in UPDATE_ORDER.
final class CollectingNeighborUpdater {
    static final Direction[] UPDATE_ORDER = new Direction[]{Direction.WEST, Direction.EAST, Direction.DOWN, Direction.UP, Direction.NORTH, Direction.SOUTH};
    private final Level level;
    private final int maxChainedNeighborUpdates;
    private final ArrayDeque<MultiNeighborUpdate> stack = new ArrayDeque<>();
    private final List<MultiNeighborUpdate> addedThisLayer = new ArrayList<>();
    private int count = 0;
    CollectingNeighborUpdater(Level level, int maxChainedNeighborUpdates) { this.level = level; this.maxChainedNeighborUpdates = maxChainedNeighborUpdates; }
    void updateNeighborsAtExceptFromFacing(BlockPos pos, Block block, Direction facing) { this.addAndRun(pos, new MultiNeighborUpdate(pos, block, facing)); }
    private void addAndRun(BlockPos pos, MultiNeighborUpdate updates) {
        boolean flag = this.count > 0;
        boolean flag1 = this.maxChainedNeighborUpdates >= 0 && this.count >= this.maxChainedNeighborUpdates;
        this.count++;
        if (!flag1) {
            if (flag) {
                this.addedThisLayer.add(updates);
            } else {
                this.stack.push(updates);
            }
        } else if (this.count - 1 == this.maxChainedNeighborUpdates) {
            level.skippedNeighborUpdates = true;
        }
        if (!flag) {
            this.runUpdates();
        }
    }
    private void runUpdates() {
        try {
            while (!this.stack.isEmpty() || !this.addedThisLayer.isEmpty()) {
                for (int i = this.addedThisLayer.size() - 1; i >= 0; i--) {
                    this.stack.push(this.addedThisLayer.get(i));
                }
                this.addedThisLayer.clear();
                MultiNeighborUpdate updates = this.stack.peek();
                while (this.addedThisLayer.isEmpty()) {
                    if (!updates.runNext(this.level)) {
                        this.stack.pop();
                        break;
                    }
                }
            }
        } finally {
            this.stack.clear();
            this.addedThisLayer.clear();
            this.count = 0;
        }
    }
    static final class MultiNeighborUpdate {
        private final BlockPos sourcePos;
        private final Block sourceBlock;
        private final Direction skipDirection;
        private int idx = 0;
        MultiNeighborUpdate(BlockPos sourcePos, Block sourceBlock, Direction skipDirection) {
            this.sourcePos = sourcePos;
            this.sourceBlock = sourceBlock;
            this.skipDirection = skipDirection;
            if (UPDATE_ORDER[this.idx] == skipDirection) {
                this.idx++;
            }
        }
        // NeighborUpdater.executeUpdate (contract-checked) calls handleNeighborChanged on the neighbor's current state.
        boolean runNext(Level level) {
            BlockPos blockpos = this.sourcePos.relative(UPDATE_ORDER[this.idx++]);
            BlockState blockstate = level.getBlockState(blockpos);
            blockstate.handleNeighborChanged(level, blockpos, this.sourceBlock, this.sourcePos, false);
            if (this.idx < UPDATE_ORDER.length && UPDATE_ORDER[this.idx] == this.skipDirection) {
                this.idx++;
            }
            return this.idx < UPDATE_ORDER.length;
        }
    }
}
// RandomSource.nextFloat with a scripted sequence and a fallback value.
final class RandomSource {
    final ArrayDeque<Float> script = new ArrayDeque<>();
    float fallback = 0.5F;
    int calls;
    float nextFloat() { calls++; return script.isEmpty() ? fallback : script.poll(); }
}
// Counts only. BlockProcessorStandard pushes for blocks that can drop but pops for every non-air block; that mismatch is recorded, not checked.
final class ProfilerFiller { int pushes, pops; void push(String name) { pushes++; } void pop() { pops++; } }
record ExplodeCall(Entity source, double x, double y, double z, float radius, Level.ExplosionInteraction interaction) {}
class Level implements BlockGetter {
    enum ExplosionInteraction { NONE, BLOCK, MOB, TNT, TRIGGER }
    boolean isClientSide;
    final Map<BlockPos, BlockState> states = new HashMap<>();
    final Map<BlockPos, BlockEntity> blockEntities = new HashMap<>();
    final List<Drop> drops = new ArrayList<>();
    final List<AfterBreak> afterBreak = new ArrayList<>();
    final List<AfterBreakCall> afterBreakCalls = new ArrayList<>();
    final List<Step> journal = new ArrayList<>();
    final List<BreakRecord> breakEvents = new ArrayList<>();
    final List<ExplodeCall> explodeCalls = new ArrayList<>();
    // ServerLevel's updater; 1000000 is the dedicated-server default for max-chained-neighbor-updates.
    final CollectingNeighborUpdater neighborUpdater = new CollectingNeighborUpdater(this, 1_000_000);
    boolean skippedNeighborUpdates;
    final RandomSource random = new RandomSource();
    final ProfilerFiller profiler = new ProfilerFiller();
    boolean doBlockDrops = true;
    int slotDrops, silverfish, containerDrops;
    final RecipeManager recipes = new RecipeManager();
    final RegistryAccess registries = new RegistryAccess();
    HitResult clipResult = new HitResult(HitResult.Type.MISS);
    public BlockState getBlockState(BlockPos pos) { return states.getOrDefault(pos, Blocks.AIR.defaultBlockState()); }
    ProfilerFiller getProfiler() { return profiler; }
    // The regression world is fully loaded.
    boolean hasChunksAt(BlockPos from, BlockPos to) { return true; }
    // The EXPLOSION ability's cosmetic vanilla explosion (interaction NONE breaks nothing); recorded only.
    void explode(Entity source, double x, double y, double z, float radius, ExplosionInteraction interaction) { explodeCalls.add(new ExplodeCall(source, x, y, z, radius, interaction)); }
    BlockEntity getBlockEntity(BlockPos pos) { return blockEntities.get(pos); }
    void removeBlockEntity(BlockPos pos) { BlockEntity be = blockEntities.remove(pos); if(be != null) be.removed = true; }
    RegistryAccess registryAccess() { return registries; }
    RecipeManager getRecipeManager() { return recipes; }
    HitResult clip(ClipContext context) { return clipResult; }
    // Level.setBlock -> LevelChunk.setBlockState (contract-checked): an unchanged state returns false; otherwise the new state
    // is stored first and the server then calls the old state's onRemove while its block entity is still registered.
    // Level.markAndNotifyBlock then (contract-checked), only while the stored state is still the new one and with flag 1, runs
    // ServerLevel.blockUpdated -> updateNeighborsAt -> neighborUpdater.updateNeighborsAtExceptFromFacing(pos, old block, null).
    // NeoForge's NeighborNotifyEvent is posted there but its cancellation is ignored; shape updates, client sync and comparator
    // updates are not modeled.
    boolean setBlock(BlockPos pos, BlockState state, int flags) {
        BlockState old = getBlockState(pos);
        if(old == state) return false;
        if(state.isAir()) states.remove(pos); else states.put(pos, state);
        journal.add(new Step("set", pos, state));
        if(!isClientSide) old.onRemove(this, pos, state, (flags & 64) != 0);
        if(getBlockState(pos) == state && (flags & 1) != 0 && !isClientSide) neighborUpdater.updateNeighborsAtExceptFromFacing(pos, old.getBlock(), null);
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
interface Container {}
final class Containers {
    static void dropContents(Level level, BlockPos pos, BarrelBlockEntity barrel) {
        level.slotDrops += barrel.inventory;
        if(barrel.inventory > 0) level.journal.add(new Step("slots", pos, barrel.inventory));
        barrel.inventory = 0;
    }
    // Containers.dropContents -> dropItemStack (contract-checked): each slot stack leaves at the block's position and is split down to
    // empty. The game spawns several item entities per stack; one Drop of the whole stack stands for them.
    static void dropContents(Level level, BlockPos pos, CrateBaseBlockEntity crate) {
        for(ItemStack stack : crate.slots) {
            if(stack.isEmpty()) continue;
            Drop drop = new Drop(pos, stack.copy());
            level.drops.add(drop);
            level.journal.add(new Step("drop", pos, drop));
            stack.setCount(0);
        }
    }
    // Containers.dropContentsOnDestroy (contract-checked): only a Container block entity drops its slots. No block entity of this world
    // is a Container, so DummyableBlock.onRemove drops no slot contents here.
    static void dropContentsOnDestroy(BlockState state, BlockState newState, Level level, BlockPos pos) {
        if (!state.is(newState.getBlock())) {
            if (level.getBlockEntity(pos) instanceof Container) level.containerDrops++;
        }
    }
}
// Explosion.finalizeExplosion's block part (contract-checked). The game shuffles toBlow; the caller supplies the order instead.
// ExplosionVNT also uses one as its vanilla-compatible `compat` explosion.
final class Explosion {
    final ServerLevel level; final List<BlockPos> toBlow;
    Explosion(ServerLevel level, List<BlockPos> toBlow) { this.level = level; this.toBlow = toBlow; }
    List<BlockPos> getToBlow() { return toBlow; }
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
class Item {
    public boolean mineBlock(ItemStack stack, Level level, BlockState state, BlockPos pos, LivingEntity miningEntity) { return false; }
    // Item.canAttackBlock default (ToolAbilityItem does not override it).
    boolean canAttackBlock(BlockState state, Level level, BlockPos pos, Player player) { return true; }
}
// ExplosionVNT, reduced to what the EXPLOSION ability uses. explode() keeps the source order (source-checked): allocate, add the blocks
// to the compat explosion, then process; no entity processor or effects are set here.
interface IBlockAllocator { HashSet<BlockPos> allocate(ExplosionVNT explosion, Level level, double x, double y, double z, float size); }
interface IBlockProcessor { void process(ExplosionVNT explosion, Level level, double x, double y, double z, HashSet<BlockPos> affectedBlocks); }
interface IDropChanceMutator { float mutateDropChance(ExplosionVNT explosion, Block block, BlockPos pos, float chance); }
interface IFortuneMutator { int mutateFortune(ExplosionVNT explosion, Block block, BlockPos pos); }
interface IBlockMutator { void mutatePre(ExplosionVNT explosion, BlockState state, BlockPos pos); void mutatePost(ExplosionVNT explosion, BlockPos pos); }
class ExplosionVNT {
    private IBlockAllocator blockAllocator;
    private IBlockProcessor blockProcessor;
    public Level level;
    public double x, y, z;
    public float size;
    public Explosion compat;
    ExplosionVNT(Level level, double x, double y, double z, float size) {
        this.level = level; this.x = x; this.y = y; this.z = z; this.size = size;
        this.compat = new Explosion((ServerLevel) level, new ArrayList<>());
    }
    void explode() {
        boolean processBlocks = blockAllocator != null && blockProcessor != null;
        HashSet<BlockPos> affectedBlocks = null;
        if(processBlocks) affectedBlocks = blockAllocator.allocate(this, level, x, y, z, size);
        if(processBlocks) this.compat.getToBlow().addAll(affectedBlocks);
        if(processBlocks) blockProcessor.process(this, level, x, y, z, affectedBlocks);
    }
    ExplosionVNT setBlockAllocator(IBlockAllocator blockAllocator) { this.blockAllocator = blockAllocator; return this; }
    ExplosionVNT setBlockProcessor(IBlockProcessor blockProcessor) { this.blockProcessor = blockProcessor; return this; }
}
// Stand-in for the ray allocator: the scenario's affected blocks, in the processing order it chose (a LinkedHashSet keeps it).
final class BlockAllocatorStandard implements IBlockAllocator {
    static List<BlockPos> next = List.of();
    public HashSet<BlockPos> allocate(ExplosionVNT explosion, Level level, double x, double y, double z, float size) { return new LinkedHashSet<>(next); }
}
__PROCESSOR__
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
    boolean isShears;
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
    for line in DUMMYABLE_FIELDS:
        assert text[DUMMYABLE].count(line) == 1, f"DummyableBlock field not found once: {line!r}"
    # The whole class, verbatim except that it cannot be public in the single-file world.
    processor = method(text[PROCESSOR], "public class BlockProcessorStandard implements IBlockProcessor")
    processor = processor.replace("public class BlockProcessorStandard", "class BlockProcessorStandard", 1)
    return (STUBS.replace("__HARVEST__", harvest)
            .replace("__DUMMYABLE_FIELDS__", "".join(DUMMYABLE_FIELDS).rstrip("\n"))
            .replace("__DUMMYABLE__", "\n".join("    " + method(text[DUMMYABLE], s) for s in DUMMYABLE_METHODS))
            .replace("__REFINERY__", "\n".join("    " + method(text[REFINERY], s) for s in REFINERY_METHODS))
            .replace("__CENTRIFUGE__", "\n".join("    " + method(text[CENTRIFUGE], s) for s in CENTRIFUGE_METHODS))
            .replace("__OUTGAS__", "    " + method(text[OUTGAS], "protected void spawnAfterBreak("))
            .replace("__PROCESSOR__", processor)
            .replace("__AREA__", area)
            .replace("__TOOL__", "\n".join("    " + method(text[TOOL], s) for s in TOOL_METHODS))
            .replace("__PERSISTENT__", persistent)
            .replace("__COMPAT__", "    " + method(text[COMPAT], "public static BlockEntity getCoreFromPos("))
            .replace("__BARREL_BE__", "\n".join("    " + method(text[BARREL_BE], s) for s in BARREL_BE_METHODS))
            .replace("__BARREL__", "\n".join("    " + method(text[BARREL], s) for s in BARREL_METHODS))
            .replace("__CRATE_BE__", "\n".join("    " + method(text[CRATE_BE], s) for s in CRATE_BE_METHODS))
            .replace("__CRATE__", "\n".join("    " + method(text[CRATE], s) for s in CRATE_METHODS)))
