"""Goal20C minimal compile world: the stand-ins the production FuelPoolRecipes, FuelPoolRecipeClientSync and MachineWasteDrumBlockEntity
compile against, without Minecraft, NeoForge or the older isolated worlds. Gson is the real jar. Two production bodies are carried verbatim
from the live sources (SerializableRecipe.readRecipeStream and readRecipeLenient), so the lenient config-file path is the production one.

Every stand-in is written under the run directory; none shadows a production source (the verifier checks this)."""
import re

# Production sources compiled unchanged.
PRODUCTION = (
    'com/hbm/inventory/recipes/FuelPoolRecipes.java',
    'com/hbm/handler/FuelPoolRecipeClientSync.java',
    'com/hbm/blockentity/machine/MachineWasteDrumBlockEntity.java',
)

STAND_INS = [
    'Item / ItemStack / Items.AIR: an item is its registry id; the stack carries an optional META patch beside an item default (DepletedFuelItem '
    'defaults to META 0 like the production component), and setMeta to the default removes the patch like PatchedDataComponentMap.set',
    'MetaHelper: getMeta = patch or item default or 0 (production getOrDefault(META, 0)); setMeta; newStack; WILDCARD_VALUE = Short.MAX_VALUE',
    'BuiltInRegistries.ITEM: a defaulted registry (default minecraft:air) holding every NtmItems id parsed from the production NtmItems.java plus '
    'minecraft:air and minecraft:stone; NtmItems is a generated holder class with one DeferredItem per production field',
    'ResourceLocation.parse: the vanilla 1.21.1 bySeparator/createUntrusted/withDefaultNamespace rules ([a-z0-9_.-] namespace, [a-z0-9/._-] path)',
    'SerializableRecipe: the abstract surface FuelPoolRecipes overrides, the real Gson instance and the production readRecipeStream and '
    'readRecipeLenient bodies verbatim; NuclearTechMod.LOGGER records error() calls for the fixture',
    'MachineBaseBlockEntity: slots (NonNullList), level, worldPosition, getItem, a setChanged counter and the production default face rules '
    '(canTakeItemThroughFace false, getSlotsForFace {0}); Container.getMaxStackSize default 99 as in 1.21.1',
    'Level: isClientSide, a replaceable random, isLoaded over declared unloaded positions, getFluidState over a position -> fluid map (reads of '
    'unloaded positions are recorded); Fluids EMPTY/WATER/FLOWING_WATER/LAVA/FLOWING_LAVA; Direction in the vanilla order DOWN, UP, NORTH, '
    'SOUTH, WEST, EAST with the vanilla steps; BlockPos.relative',
    'MachineWasteDrumMenu, Component, Inventory, Player, AbstractContainerMenu, BlockState, BlockEntityType, NtmBlockEntityTypes: inert holders',
    'NeoForge annotations (EventBusSubscriber, SubscribeEvent, Dist) and ClientPlayerNetworkEvent.LoggingOut: empty declarations so the production '
    'FuelPoolRecipeClientSync compiles; no event bus runs',
]


def method_text(text, signature):
    """The full text of the method starting at `signature` (exactly once), through its matching closing brace."""
    if text.count(signature) != 1: raise SystemExit(f'Production anchor not found exactly once: {signature!r}')
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0: return text[start:i + 1]
    raise SystemExit('Unbalanced braces after ' + signature)


def stubs(serializable_text, items, depleted_constants):
    """relative path -> Java text. items: NtmItems field -> id (production registrations); depleted_constants: {'COOL': n, 'HOT': n}."""
    serializable = serializable_text.replace('\r\n', '\n')
    stream = method_text(serializable, '    public void readRecipeStream(Reader reader) {')
    lenient = method_text(serializable, '    protected boolean readRecipeLenient(JsonElement row, int index) {')
    s = {}
    s['javax/annotation/Nullable.java'] = '''package javax.annotation;
import java.lang.annotation.*;
@Retention(RetentionPolicy.CLASS) @Target({ElementType.METHOD, ElementType.PARAMETER, ElementType.FIELD, ElementType.LOCAL_VARIABLE})
public @interface Nullable {}'''
    s['net/neoforged/api/distmarker/Dist.java'] = 'package net.neoforged.api.distmarker;\npublic enum Dist { CLIENT, DEDICATED_SERVER }'
    s['net/neoforged/bus/api/SubscribeEvent.java'] = '''package net.neoforged.bus.api;
import java.lang.annotation.*;
@Retention(RetentionPolicy.RUNTIME) @Target(ElementType.METHOD)
public @interface SubscribeEvent {}'''
    s['net/neoforged/fml/common/EventBusSubscriber.java'] = '''package net.neoforged.fml.common;
import java.lang.annotation.*;
import net.neoforged.api.distmarker.Dist;
@Retention(RetentionPolicy.RUNTIME) @Target(ElementType.TYPE)
public @interface EventBusSubscriber { String modid() default ""; Dist[] value() default { Dist.CLIENT, Dist.DEDICATED_SERVER }; }'''
    s['net/neoforged/neoforge/client/event/ClientPlayerNetworkEvent.java'] = '''package net.neoforged.neoforge.client.event;
public class ClientPlayerNetworkEvent {
    public static class LoggingOut extends ClientPlayerNetworkEvent {}
}'''
    s['com/hbm/main/NuclearTechMod.java'] = '''package com.hbm.main;
import java.util.ArrayList;
import java.util.List;
public class NuclearTechMod {
    public static final String MODID = "hbmsntm";
    public static final Logger LOGGER = new Logger();
    public static final class Logger {
        public final List<String> errors = new ArrayList<>();
        public void error(String format, Object... args) {
            StringBuilder out = new StringBuilder(format);
            for(Object arg : args) {
                int at = out.indexOf("{}");
                if(at >= 0) out.replace(at, at + 2, String.valueOf(arg)); else if(arg instanceof Throwable t) out.append(" | ").append(t.getMessage());
            }
            errors.add(out.toString());
        }
    }
}'''
    s['net/minecraft/ResourceLocationException.java'] = 'package net.minecraft;\npublic class ResourceLocationException extends RuntimeException { public ResourceLocationException(String m) { super(m); } }'
    s['net/minecraft/resources/ResourceLocation.java'] = '''package net.minecraft.resources;
import net.minecraft.ResourceLocationException;
public final class ResourceLocation {
    private final String namespace, path;
    private ResourceLocation(String namespace, String path) { this.namespace = namespace; this.path = path; }
    public static ResourceLocation parse(String location) { return bySeparator(location, ':'); }
    public static ResourceLocation bySeparator(String location, char separator) {
        int i = location.indexOf(separator);
        if(i >= 0) {
            String path = location.substring(i + 1);
            if(i != 0) return createUntrusted(location.substring(0, i), path);
            return withDefaultNamespace(path);
        }
        return withDefaultNamespace(location);
    }
    public static ResourceLocation withDefaultNamespace(String path) { return new ResourceLocation("minecraft", assertValidPath("minecraft", path)); }
    public static ResourceLocation fromNamespaceAndPath(String namespace, String path) { return createUntrusted(namespace, path); }
    private static ResourceLocation createUntrusted(String namespace, String path) {
        if(!isValidNamespace(namespace)) throw new ResourceLocationException("Non [a-z0-9_.-] character in namespace of location: " + namespace + ":" + path);
        return new ResourceLocation(namespace, assertValidPath(namespace, path));
    }
    private static String assertValidPath(String namespace, String path) {
        for(int i = 0; i < path.length(); i++) {
            char c = path.charAt(i);
            if(!(c == '_' || c == '-' || c >= 'a' && c <= 'z' || c >= '0' && c <= '9' || c == '/' || c == '.'))
                throw new ResourceLocationException("Non [a-z0-9/._-] character in path of location: " + namespace + ":" + path);
        }
        return path;
    }
    private static boolean isValidNamespace(String namespace) {
        for(int i = 0; i < namespace.length(); i++) {
            char c = namespace.charAt(i);
            if(!(c == '_' || c == '-' || c >= 'a' && c <= 'z' || c >= '0' && c <= '9' || c == '.')) return false;
        }
        return true;
    }
    public String getNamespace() { return namespace; }
    public String getPath() { return path; }
    @Override public String toString() { return namespace + ":" + path; }
    @Override public boolean equals(Object o) { return o instanceof ResourceLocation r && r.namespace.equals(namespace) && r.path.equals(path); }
    @Override public int hashCode() { return toString().hashCode(); }
}'''
    s['net/minecraft/world/item/Item.java'] = '''package net.minecraft.world.item;
public class Item {
    public final String id;
    /** Stand-in for the item's default META component (null: the item has no META default). */
    public final Integer defaultMeta;
    public Item(String id) { this(id, null); }
    public Item(String id, Integer defaultMeta) { this.id = id; this.defaultMeta = defaultMeta; }
    @Override public String toString() { return id; }
}'''
    s['net/minecraft/world/item/Items.java'] = '''package net.minecraft.world.item;
public class Items {
    public static final Item AIR = net.minecraft.core.registries.BuiltInRegistries.ITEM.register(new Item("minecraft:air"));
    public static final Item STONE = net.minecraft.core.registries.BuiltInRegistries.ITEM.register(new Item("minecraft:stone"));
    public static void bootstrap() { }
}'''
    s['net/minecraft/world/item/ItemStack.java'] = '''package net.minecraft.world.item;
public final class ItemStack {
    public static final ItemStack EMPTY = new ItemStack((Item) null, 0);
    private final Item item;
    private int count;
    private Integer metaPatch;
    public ItemStack(Item item) { this(item, 1); }
    public ItemStack(Item item, int count) { this.item = item; this.count = count; }
    public boolean isEmpty() { return this == EMPTY || item == null || item == Items.AIR || count <= 0; }
    public Item getItem() { return isEmpty() ? Items.AIR : item; }
    public int getCount() { return isEmpty() ? 0 : count; }
    public void setCount(int count) { this.count = count; }
    public ItemStack copy() {
        if(isEmpty()) return EMPTY;
        ItemStack copy = new ItemStack(item, count);
        copy.metaPatch = metaPatch;
        return copy;
    }
    public ItemStack copyWithCount(int count) {
        if(isEmpty()) return EMPTY;
        ItemStack copy = copy();
        copy.setCount(count);
        return copy;
    }
    /** The META patch (null when the stack uses the item default). */
    public Integer metaPatch() { return metaPatch; }
    public int metaValue() { return metaPatch != null ? metaPatch : getItem().defaultMeta != null ? getItem().defaultMeta : 0; }
    /** PatchedDataComponentMap.set: a value equal to the prototype removes the patch. */
    public void setMetaComponent(int meta) { metaPatch = Integer.valueOf(meta).equals(getItem().defaultMeta) ? null : meta; }
    @Override public String toString() { return isEmpty() ? "EMPTY" : count + "x" + item.id + "@" + metaValue() + (metaPatch != null ? "(patch)" : ""); }
}'''
    s['net/minecraft/core/registries/BuiltInRegistries.java'] = '''package net.minecraft.core.registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import java.util.LinkedHashMap;
import java.util.Map;
public class BuiltInRegistries {
    public static final ItemRegistry ITEM = new ItemRegistry();
    // Class-initialisation order: ITEM is assigned before the holders register into it, whichever class is touched first.
    static { net.minecraft.world.item.Items.bootstrap(); com.hbm.items.NtmItems.bootstrap(); }
    public static final class ItemRegistry {
        private final Map<String, Item> byId = new LinkedHashMap<>();
        public <T extends Item> T register(T item) {
            if(byId.putIfAbsent(item.id, item) != null) throw new IllegalStateException("duplicate stand-in id " + item.id);
            return item;
        }
        public boolean containsKey(ResourceLocation id) { return byId.containsKey(id.toString()); }
        /** Defaulted registry: an unknown id yields air. */
        public Item get(ResourceLocation id) { Item item = byId.get(id.toString()); return item != null ? item : byId.get("minecraft:air"); }
        public ResourceLocation getKey(Item item) { return ResourceLocation.parse(byId.get(item.id) == item ? item.id : "minecraft:air"); }
        public int size() { return byId.size(); }
    }
}'''
    s['net/neoforged/neoforge/registries/DeferredItem.java'] = '''package net.neoforged.neoforge.registries;
import net.minecraft.world.item.Item;
public class DeferredItem<T extends Item> implements java.util.function.Supplier<T> {
    private final T item;
    public DeferredItem(T item) { this.item = item; }
    public T get() { return item; }
}'''
    s['com/hbm/inventory/MetaHelper.java'] = '''package com.hbm.inventory;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
public class MetaHelper {
    public static final int WILDCARD_VALUE = Short.MAX_VALUE;
    public static int getMeta(ItemStack stack) { return stack.metaValue(); }
    public static void setMeta(ItemStack stack, int meta) { stack.setMetaComponent(meta); }
    public static ItemStack newStack(Item item, int count, int meta) { ItemStack stack = new ItemStack(item, count); setMeta(stack, meta); return stack; }
}'''
    s['com/hbm/items/machine/DepletedFuelItem.java'] = f'''package com.hbm.items.machine;
import net.minecraft.world.item.Item;
/** Stand-in: the production constants (parsed by the verifier) and the META default COOL. */
public class DepletedFuelItem extends Item {{
    public static final int COOL = {depleted_constants['COOL']};
    public static final int HOT = {depleted_constants['HOT']};
    public DepletedFuelItem(String id) {{ super(id, COOL); }}
}}'''
    fields = []
    for field, ident in sorted(items.items()):
        kind = 'DepletedFuelItem' if field.startswith('WASTE_') else 'Item'
        fields.append(f'    public static final DeferredItem<Item> {field} = reg(new {kind}("hbmsntm:{ident}"));')
    s['com/hbm/items/NtmItems.java'] = ('package com.hbm.items;\nimport com.hbm.items.machine.DepletedFuelItem;\nimport net.minecraft.core.registries.BuiltInRegistries;\n'
                                        'import net.minecraft.world.item.Item;\nimport net.neoforged.neoforge.registries.DeferredItem;\n'
                                        '/** Generated stand-in: one holder per production NtmItems field, id from the production registration. */\npublic class NtmItems {\n'
                                        '    private static DeferredItem<Item> reg(Item item) { return new DeferredItem<>(BuiltInRegistries.ITEM.register(item)); }\n'
                                        '    public static void bootstrap() { }\n' + '\n'.join(fields) + '\n}')
    s['com/hbm/inventory/recipes/loader/SerializableRecipe.java'] = f'''package com.hbm.inventory.recipes.loader;
import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.stream.JsonWriter;
import com.hbm.main.NuclearTechMod;
import java.io.*;
/** Stand-in surface; readRecipeStream and readRecipeLenient are the production bodies verbatim. */
public abstract class SerializableRecipe {{
    public static final Gson gson = new Gson();
    public abstract String getFileName();
    public abstract Object getRecipeObject();
    public abstract void readRecipe(JsonElement recipe);
    public abstract void writeRecipe(Object recipe, JsonWriter writer) throws IOException;
    public abstract void registerDefaults();
    public abstract void deleteRecipes();
    public String getComment() {{ return null; }}

{stream}

{lenient}
}}'''
    s['net/minecraft/core/NonNullList.java'] = '''package net.minecraft.core;
import java.util.ArrayList;
import java.util.Collections;
public class NonNullList<E> {
    private final ArrayList<E> list;
    private NonNullList(ArrayList<E> list) { this.list = list; }
    public static <E> NonNullList<E> withSize(int size, E fill) { return new NonNullList<>(new ArrayList<>(Collections.nCopies(size, fill))); }
    public E get(int i) { return list.get(i); }
    public E set(int i, E value) { if(value == null) throw new NullPointerException(); return list.set(i, value); }
    public int size() { return list.size(); }
}'''
    s['net/minecraft/core/Direction.java'] = '''package net.minecraft.core;
public enum Direction {
    DOWN(0, -1, 0), UP(0, 1, 0), NORTH(0, 0, -1), SOUTH(0, 0, 1), WEST(-1, 0, 0), EAST(1, 0, 0);
    private final int x, y, z;
    Direction(int x, int y, int z) { this.x = x; this.y = y; this.z = z; }
    public int getStepX() { return x; } public int getStepY() { return y; } public int getStepZ() { return z; }
}'''
    s['net/minecraft/core/BlockPos.java'] = '''package net.minecraft.core;
public final class BlockPos {
    private final int x, y, z;
    public BlockPos(int x, int y, int z) { this.x = x; this.y = y; this.z = z; }
    public int getX() { return x; } public int getY() { return y; } public int getZ() { return z; }
    public BlockPos relative(Direction d) { return new BlockPos(x + d.getStepX(), y + d.getStepY(), z + d.getStepZ()); }
    @Override public boolean equals(Object o) { return o instanceof BlockPos p && p.x == x && p.y == y && p.z == z; }
    @Override public int hashCode() { return (x * 31 + y) * 31 + z; }
    @Override public String toString() { return "(" + x + "," + y + "," + z + ")"; }
}'''
    s['net/minecraft/util/RandomSource.java'] = 'package net.minecraft.util;\npublic interface RandomSource { int nextInt(int bound); }'
    s['net/minecraft/world/level/material/Fluid.java'] = 'package net.minecraft.world.level.material;\npublic class Fluid { public final String id; public Fluid(String id) { this.id = id; } public String toString() { return id; } }'
    s['net/minecraft/world/level/material/Fluids.java'] = '''package net.minecraft.world.level.material;
public class Fluids {
    public static final Fluid EMPTY = new Fluid("minecraft:empty");
    public static final Fluid FLOWING_WATER = new Fluid("minecraft:flowing_water");
    public static final Fluid WATER = new Fluid("minecraft:water");
    public static final Fluid FLOWING_LAVA = new Fluid("minecraft:flowing_lava");
    public static final Fluid LAVA = new Fluid("minecraft:lava");
}'''
    s['net/minecraft/world/level/material/FluidState.java'] = 'package net.minecraft.world.level.material;\npublic final class FluidState { private final Fluid type; public FluidState(Fluid type) { this.type = type; } public Fluid getType() { return type; } }'
    s['net/minecraft/world/level/Level.java'] = '''package net.minecraft.world.level;
import net.minecraft.core.BlockPos;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.material.Fluid;
import net.minecraft.world.level.material.FluidState;
import net.minecraft.world.level.material.Fluids;
import java.util.*;
public class Level {
    public boolean isClientSide;
    public RandomSource random;
    public final Map<BlockPos, Fluid> fluids = new HashMap<>();
    public final Set<BlockPos> unloaded = new HashSet<>();
    public final List<BlockPos> unloadedReads = new ArrayList<>();
    public boolean isLoaded(BlockPos pos) { return !unloaded.contains(pos); }
    public FluidState getFluidState(BlockPos pos) {
        if(unloaded.contains(pos)) unloadedReads.add(pos);
        return new FluidState(fluids.getOrDefault(pos, Fluids.EMPTY));
    }
}'''
    s['net/minecraft/world/level/block/state/BlockState.java'] = 'package net.minecraft.world.level.block.state;\npublic class BlockState {}'
    s['net/minecraft/world/level/block/entity/BlockEntityType.java'] = 'package net.minecraft.world.level.block.entity;\npublic class BlockEntityType<T> {}'
    s['net/minecraft/network/chat/Component.java'] = '''package net.minecraft.network.chat;
public final class Component {
    public final String key;
    private Component(String key) { this.key = key; }
    public static Component translatable(String key) { return new Component(key); }
}'''
    s['net/minecraft/world/entity/player/Inventory.java'] = 'package net.minecraft.world.entity.player;\npublic class Inventory {}'
    s['net/minecraft/world/entity/player/Player.java'] = 'package net.minecraft.world.entity.player;\npublic class Player {}'
    s['net/minecraft/world/inventory/AbstractContainerMenu.java'] = 'package net.minecraft.world.inventory;\npublic class AbstractContainerMenu {}'
    s['com/hbm/inventory/menus/MachineWasteDrumMenu.java'] = '''package com.hbm.inventory.menus;
import com.hbm.blockentity.machine.MachineWasteDrumBlockEntity;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.inventory.AbstractContainerMenu;
public class MachineWasteDrumMenu extends AbstractContainerMenu {
    public final MachineWasteDrumBlockEntity be;
    public MachineWasteDrumMenu(int id, Inventory inventory, MachineWasteDrumBlockEntity be) { this.be = be; }
}'''
    s['com/hbm/blockentity/NtmBlockEntityTypes.java'] = '''package com.hbm.blockentity;
import com.hbm.blockentity.machine.MachineWasteDrumBlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityType;
import java.util.function.Supplier;
public class NtmBlockEntityTypes {
    private static final BlockEntityType<MachineWasteDrumBlockEntity> DRUM = new BlockEntityType<>();
    public static final Supplier<BlockEntityType<MachineWasteDrumBlockEntity>> MACHINE_WASTE_DRUM = () -> DRUM;
}'''
    s['com/hbm/blockentity/MachineBaseBlockEntity.java'] = '''package com.hbm.blockentity;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.NonNullList;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import javax.annotation.Nullable;
/** Stand-in: the production MachineBaseBlockEntity inventory surface; level and worldPosition are the vanilla BlockEntity fields. */
public abstract class MachineBaseBlockEntity {
    public NonNullList<ItemStack> slots;
    public Level level;
    public final BlockPos worldPosition;
    public int setChangedCalls;
    public MachineBaseBlockEntity(BlockEntityType<?> type, BlockPos pos, BlockState state, int size) {
        this.worldPosition = pos;
        this.slots = NonNullList.withSize(size, ItemStack.EMPTY);
    }
    protected abstract Component getDefaultName();
    public Component defaultName() { return getDefaultName(); }
    public int getContainerSize() { return slots.size(); }
    public ItemStack getItem(int slot) { return slots.get(slot); }
    public void setChanged() { setChangedCalls++; }
    public int getMaxStackSize() { return 99; }
    public boolean canPlaceItem(int slot, ItemStack stack) { return false; }
    public int[] getSlotsForFace(Direction direction) { return new int[] { 0 }; }
    public boolean canPlaceItemThroughFace(int index, ItemStack stack, @Nullable Direction direction) { return this.canPlaceItem(index, stack); }
    public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction) { return false; }
    public abstract AbstractContainerMenu createMenu(int id, Inventory inventory, Player player);
    public abstract void updateEntity();
}'''
    return s
