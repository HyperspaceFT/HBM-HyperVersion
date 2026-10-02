"""Goal 10B stand-ins for two compile worlds.

* anvil: the Goal 3A anvil stand-ins (real AnvilRecipes, AnvilSmithingRecipe and AnvilSmithingCastMoldRecipe), with
  CastPlateItem.Type and BoltItem.Type generated from the production enums and the production castPlateIngredient
  rule, so the soldering station entry can be read with its real META values.
* machine: the Goal 9B services (energy and fluid networks, cables, battery socket, proxies, MachineBaseBlockEntity)
  plus what the soldering station, the arc welder, their recipe tables, MachineArcWelderBlock and MultiblockHandlerXR
  need. DummyableBlock is a stand-in whose fillSpace and makeExtra are the production method bodies, copied from
  DummyableBlock.java when the stand-ins are built.

See goal10b_regression/README.md for what each stand-in models.
"""

import re

from goal3a_regression.anvil_stubs import make_anvil_stubs
from goal8_regression.stubs import _fields
from goal9b_regression.stubs import build_stubs as goal9b_stubs
from verify_goal2 import STUBS as GOAL2_STUBS

ANVIL = "com/hbm/inventory/recipes/anvil/AnvilRecipes.java"
SOLDERING = "com/hbm/inventory/recipes/SolderingRecipes.java"
ARC_WELDER = "com/hbm/inventory/recipes/ArcWelderRecipes.java"


def _require(text, old, label):
    if old not in text:
        raise SystemExit(f"Goal 10B stub anchor missing in {label}: {old[:60]}")
    return text


def _replace(stubs, name, old, new):
    stubs[name] = _require(stubs[name], old, name).replace(old, new)


def enum_constants(source, label):
    """The constants of `public enum Type` in a production item class, as (name, first argument or None)."""
    match = re.search(r"public enum Type\b[^{]*\{(.*?);", source, re.S)
    if match is None:
        raise SystemExit(f"Goal 10B: no enum Type in {label}")
    body = re.sub(r"//[^\n]*", "", match.group(1))
    found = [(name, args.split(",")[0].strip() if args else None)
             for name, args in re.findall(r"\b([A-Z][A-Z0-9_]*)\s*(?:\(([^)]*)\))?\s*(?:,|$)", body.strip())]
    if not found:
        raise SystemExit(f"Goal 10B: enum Type in {label} has no constants")
    return found


def ordinal_enum(source, package, cls, label):
    """A stand-in enum whose ordinals are the production ordinals (CastPlateItem META is the ordinal)."""
    names = ",".join(name for name, _ in enum_constants(source, label))
    return f"package {package};public class {cls}{{public enum Type{{{names}}}}}"


def meta_enum(source, package, cls, label):
    """A stand-in enum carrying the production `meta` value of each constant (its first constructor argument)."""
    constants = enum_constants(source, label)
    if any(arg is None or not re.fullmatch(r"-?\d+", arg) for _, arg in constants):
        raise SystemExit(f"Goal 10B: {label} enum constants do not start with an int meta")
    body = ",".join(f"{name}({arg})" for name, arg in constants)
    return f"package {package};public class {cls}{{public enum Type{{{body};public final int meta;Type(int m){{meta=m;}}}}}}"


def method_body(source, signature, label):
    """The text of one production method, from its signature to the matching closing brace."""
    start = source.find(signature)
    if start < 0 or source.find(signature, start + 1) >= 0:
        raise SystemExit(f"Goal 10B: method not found once in {label}: {signature}")
    depth, i = 0, source.index("{", start)
    while True:
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
        i += 1


def build_anvil_stubs(source, head_anvil):
    """Goal 3A anvil world for the live AnvilRecipes and the HEAD copy (both texts provide the registry names)."""
    live = (source / ANVIL).read_text(encoding="utf-8")
    stubs = {name: GOAL2_STUBS[name] for name in (
        "net/minecraft/core/NonNullList.java", "net/minecraft/world/InteractionHand.java",
        "net/minecraft/world/entity/LivingEntity.java", "net/minecraft/network/RegistryFriendlyByteBuf.java",
    )}
    stubs.update(make_anvil_stubs(live + "\n" + head_anvil))
    stubs["com/hbm/items/CastPlateItem.java"] = ordinal_enum(
        (source / "com/hbm/items/CastPlateItem.java").read_text(encoding="utf-8"), "com.hbm.items", "CastPlateItem", "CastPlateItem")
    stubs["com/hbm/items/BoltItem.java"] = meta_enum(
        (source / "com/hbm/items/BoltItem.java").read_text(encoding="utf-8"), "com.hbm.items", "BoltItem", "BoltItem")
    # Production NtmItems.java castPlateIngredient: the cast_plate item with META = the type's ordinal.
    _replace(stubs, "com/hbm/items/NtmItems.java",
             'public static AStack castPlateIngredient(CastPlateItem.Type type,int count){return new ComparableStack(new Item("cast_plate_"+type),count);}',
             "public static AStack castPlateIngredient(CastPlateItem.Type type,int count){return new ComparableStack(CAST_PLATE.get(),count,type.ordinal());}")
    return stubs


def build_machine_stubs(source, extra_sources=()):
    """Goal 9B world plus the soldering station, arc welder, their recipe tables and the arc welder block."""
    stubs = goal9b_stubs(source)
    texts = [(source / name).read_text(encoding="utf-8") for name in (
        SOLDERING, ARC_WELDER, "com/hbm/blockentity/machine/MachineSolderingStationBlockEntity.java",
        "com/hbm/blockentity/machine/MachineArcWelderBlockEntity.java", "com/hbm/blocks/machine/MachineArcWelderBlock.java")]
    texts.extend(extra_sources)
    joined = "\n".join(texts)

    # ---- Registry entries -----------------------------------------------------------------------------------------
    _replace(stubs, "com/hbm/blockentity/NtmBlockEntityTypes.java", "BATTERY_SOCKET=new Ref()",
             "BATTERY_SOCKET=new Ref(),MACHINE_SOLDERING_STATION=new Ref(),MACHINE_ARC_WELDER=new Ref()")
    items = stubs["com/hbm/items/NtmItems.java"]
    wanted = set(re.findall(r"NtmItems\.([A-Z][A-Z_0-9]+)", joined)) | {"CAST_PLATE", "CAST_PLATE_WELDED", "WIRE_DENSE", "PART_GENERIC"}
    items = _require(items, "FLUID_IDENTIFIER_MULTI=", "NtmItems").replace(
        "FLUID_IDENTIFIER_MULTI=", _fields(items, wanted, lambda n: f'{n}=new Ref("hbmsntm:{n.lower()}"),') + "FLUID_IDENTIFIER_MULTI=", 1)
    # SolderingRecipes takes DeferredItem<Item>; the registry references are DeferredItems, as NtmItems' fields are.
    # castPlateWeldedIngredient is production NtmItems.java:1158-1160.
    items = _require(items, "public static class Ref implements net.minecraft.world.level.ItemLike{", "NtmItems").replace(
        "public static class Ref implements net.minecraft.world.level.ItemLike{",
        "public static com.hbm.inventory.RecipesCommon.AStack castPlateWeldedIngredient(com.hbm.items.CastPlateItem.Type t,int n){"
        "return new com.hbm.inventory.RecipesCommon.ComparableStack(CAST_PLATE_WELDED.get(),n,t.ordinal());}"
        "public static class Ref extends net.neoforged.neoforge.registries.DeferredItem<Item> implements net.minecraft.world.level.ItemLike{")
    stubs["com/hbm/items/NtmItems.java"] = items
    stubs["net/neoforged/neoforge/registries/DeferredItem.java"] = (
        "package net.neoforged.neoforge.registries;public abstract class DeferredItem<T extends net.minecraft.world.item.Item>"
        " implements java.util.function.Supplier<T>{public abstract T get();}")
    blocks = stubs["com/hbm/blocks/NtmBlocks.java"]
    anchor = "public static final Ref MACHINE_ASSEMBLY_MACHINE=new Ref(\"MACHINE_ASSEMBLY_MACHINE\");"
    extra = _fields(blocks, set(re.findall(r"NtmBlocks\.([A-Z][A-Z_0-9]+)", joined)),
                    lambda n: f'public static final Ref {n}=new Ref("hbmsntm:{n.lower()}");')
    stubs["com/hbm/blocks/NtmBlocks.java"] = _require(blocks, anchor, "NtmBlocks").replace(anchor, anchor + extra)

    # ---- Item enums from production (META values) ------------------------------------------------------------------
    for cls in ("CastPlateItem", "PartGenericItem"):
        stubs[f"com/hbm/items/{cls}.java"] = ordinal_enum(
            (source / f"com/hbm/items/{cls}.java").read_text(encoding="utf-8"), "com.hbm.items", cls, cls)
    stubs["com/hbm/items/WireDenseItem.java"] = meta_enum(
        (source / "com/hbm/items/WireDenseItem.java").read_text(encoding="utf-8"), "com.hbm.items", "WireDenseItem", "WireDenseItem")

    # ---- Fluids the recipe tables name (appended; the earlier IDs stay) --------------------------------------------
    fluids = stubs["com/hbm/inventory/fluid/Fluids.java"]
    existing = [(name, int(i), lead == "true", none == "true")
                for name, i, lead, none in re.findall(r"(\w+)=new FluidType\((\d+),(true|false),(true|false)\)", fluids)]
    statics = re.search(r"static\{(.*?)\}public static FluidType\[\] getAll", fluids).group(1)
    names = [name for name, *_ in existing]
    for name in sorted(set(re.findall(r"Fluids\.([A-Z][A-Z_0-9]+)", joined))):
        if name not in names:
            names.append(name)
            existing.append((name, len(existing), False, False))
    stubs["com/hbm/inventory/fluid/Fluids.java"] = (
        "package com.hbm.inventory.fluid;public class Fluids{public static final FluidType "
        + ",".join(f"{name}=new FluidType({i},{str(lead).lower()},{str(none).lower()})" for name, i, lead, none in existing)
        + ";static{" + statics + "}public static FluidType[] getAll(){return new FluidType[]{" + ",".join(names) + "};}"
        + "public static FluidType fromID(int id){return switch(id){" + "".join(f"case {i}->{name};" for name, i, *_ in existing)
        + "default->NONE;};}public static FluidType fromNameCompat(String s){return NONE;}public static FluidType fromName(String s){return NONE;}}")

    # ---- Recipe plumbing -------------------------------------------------------------------------------------------
    # Production RecipesCommon.ComparableStack(ItemStack): item, count and META of the stack (ArcWelderRecipes' dense wire).
    _replace(stubs, "com/hbm/inventory/RecipesCommon.java", "public ComparableStack(ItemLike i){item=i.asItem();}",
             "public ComparableStack(ItemLike i){item=i.asItem();}"
             "public ComparableStack(ItemStack s){item=s.getItem();stacksize=s.getCount();meta=MetaHelper.getMeta(s);}")
    # The JSON side of SerializableRecipe is not exercised (the tables register their defaults directly).
    stubs["com/hbm/inventory/recipes/loader/SerializableRecipe.java"] = (
        "package com.hbm.inventory.recipes.loader;import com.google.gson.*;import com.google.gson.stream.JsonWriter;import java.io.IOException;"
        "import com.hbm.inventory.FluidStack;import com.hbm.inventory.RecipesCommon.AStack;import net.minecraft.world.item.ItemStack;"
        "public abstract class SerializableRecipe{public boolean modified;public abstract String getFileName();public abstract Object getRecipeObject();"
        "public abstract void readRecipe(JsonElement e);public abstract void writeRecipe(Object o,JsonWriter w)throws IOException;"
        "public abstract void registerDefaults();public abstract void deleteRecipes();public void registerPost(){}public String getComment(){return null;}"
        "public static ItemStack readItemStack(JsonArray a){return ItemStack.EMPTY;}public static void writeItemStack(ItemStack s,JsonWriter w)throws IOException{}"
        "public static AStack[] readAStackArray(JsonArray a){return new AStack[0];}public static void writeAStack(AStack s,JsonWriter w)throws IOException{}"
        "public static FluidStack readFluidStack(JsonArray a){return null;}public static void writeFluidStack(FluidStack s,JsonWriter w)throws IOException{}}")
    _replace(stubs, "com/google/gson/JsonElement.java", "public int getAsInt(){return 0;}",
             "public int getAsInt(){return 0;}public long getAsLong(){return 0;}")

    # ---- Machine plumbing ------------------------------------------------------------------------------------------
    _replace(stubs, "com/hbm/blockentity/IUpgradeInfoProvider.java", 'String KEY_SPEED="speed",',
             'String KEY_SPEED="speed",KEY_DELAY="upgrade.delay",')
    _replace(stubs, "net/minecraft/ChatFormatting.java", "GREEN}", "GREEN,DARK_GRAY}")
    # Production IFluidCopiable.getTankToPaste is a default method (the arc welder does not override it).
    _replace(stubs, "com/hbm/blockentity/IFluidCopiable.java", "FluidTank getTankToPaste();",
             "default FluidTank getTankToPaste(){return null;}")
    for menu, be in (("MachineSolderingStationMenu", "MachineSolderingStationBlockEntity"), ("MachineArcWelderMenu", "MachineArcWelderBlockEntity")):
        stubs[f"com/hbm/inventory/menus/{menu}.java"] = (
            f"package com.hbm.inventory.menus;public class {menu} extends net.minecraft.world.inventory.AbstractContainerMenu{{"
            f"public {menu}(int id,net.minecraft.world.entity.player.Inventory inv,com.hbm.blockentity.machine.{be} be){{}}}}")
    # Display stacks travel in NBT: save() wraps a copy, parse()/parseOptional() unwrap it; writeNbt/readNbt are one
    # entry in the Goal 9B ordered buffer. No registry access is modelled (registryAccess() is null).
    _replace(stubs, "net/minecraft/network/RegistryFriendlyByteBuf.java", "public void writeUtf(String n){put(n);}",
             "public void writeUtf(String n){put(n);}public void writeNbt(net.minecraft.nbt.CompoundTag t){put(t);}"
             "public net.minecraft.nbt.CompoundTag readNbt(){return (net.minecraft.nbt.CompoundTag)next();}")
    _replace(stubs, "net/minecraft/world/item/ItemStack.java", "public String component(){return \"\";}",
             "public net.minecraft.nbt.CompoundTag save(Object registries){net.minecraft.nbt.CompoundTag t=new net.minecraft.nbt.CompoundTag();t.putObject(\"stack\",copy());return t;}"
             "public static ItemStack parseOptional(Object registries,net.minecraft.nbt.CompoundTag t){Object s=t.getObject(\"stack\");return s instanceof ItemStack i?i.copy():EMPTY;}"
             "public static Optional<ItemStack> parse(Object registries,net.minecraft.nbt.CompoundTag t){Object s=t.getObject(\"stack\");return s instanceof ItemStack i?Optional.of(i.copy()):Optional.empty();}"
             "public String component(){return \"\";}")
    _replace(stubs, "net/minecraft/world/level/Level.java", "public ResourceKey<Level> dimension(){return OVERWORLD;}",
             "public ResourceKey<Level> dimension(){return OVERWORLD;}public HolderLookup.Provider registryAccess(){return null;}"
             "public final List<BlockPos> setBlocks=new ArrayList<>();"
             "public boolean setBlock(BlockPos p,BlockState s,int flags){setBlocks.add(p);states.put(p,s);return true;}")

    # ---- Blocks: states with the DummyableBlock TYPE property, MachineArcWelderBlock's supertypes ---------------------
    # FACING keeps the earlier model (an Object key read through the `facing` field, so every older fixture helper
    # still works); TYPE is an EnumProperty stored per state. setValue returns a new state, as BlockState does.
    stubs["net/minecraft/world/level/block/state/properties/EnumProperty.java"] = (
        "package net.minecraft.world.level.block.state.properties;public class EnumProperty<T>{public final T fallback;"
        "public EnumProperty(T fallback){this.fallback=fallback;}}")
    stubs["net/minecraft/world/level/block/state/BlockState.java"] = (
        "package net.minecraft.world.level.block.state;import java.util.*;import net.minecraft.core.*;"
        "import net.minecraft.world.level.block.state.properties.EnumProperty;"
        "public class BlockState{public net.minecraft.world.level.block.Block block=new net.minecraft.world.level.block.Block();"
        "public net.minecraft.world.level.block.Block getBlock(){return block;}public Direction facing=Direction.NORTH;"
        "public Direction getValue(Object k){return facing;}public final Map<Object,Object> values=new HashMap<>();"
        "@SuppressWarnings(\"unchecked\")public <T> T getValue(EnumProperty<T> k){return values.containsKey(k)?(T)values.get(k):k.fallback;}"
        "public BlockState setValue(Object k,Direction v){BlockState s=copy();s.facing=v;return s;}"
        "public <T> BlockState setValue(EnumProperty<T> k,T v){BlockState s=copy();s.values.put(k,v);return s;}"
        "private BlockState copy(){BlockState s=new BlockState();s.block=block;s.facing=facing;s.values.putAll(values);s.resistance=resistance;return s;}"
        "public boolean canBeReplaced(){return block.getClass()==net.minecraft.world.level.block.Block.class;}"
        "public boolean isAir(){return true;}public float resistance;"
        "public float getExplosionResistance(net.minecraft.world.level.Level l,BlockPos p,Object explosion){return resistance;}}")
    stubs["net/minecraft/world/level/block/Block.java"] = (
        "package net.minecraft.world.level.block;public class Block{public static class Properties{}"
        "public net.minecraft.world.level.block.state.BlockState defaultBlockState(){"
        "net.minecraft.world.level.block.state.BlockState s=new net.minecraft.world.level.block.state.BlockState();s.block=this;return s;}}")
    stubs["net/minecraft/util/StringRepresentable.java"] = (
        "package net.minecraft.util;public interface StringRepresentable{String getSerializedName();}")
    stubs["com/mojang/serialization/MapCodec.java"] = "package com.mojang.serialization;public class MapCodec<T>{}"
    stubs["net/minecraft/world/level/block/entity/BlockEntityTicker.java"] = (
        "package net.minecraft.world.level.block.entity;public interface BlockEntityTicker<T extends BlockEntity>{"
        "void tick(net.minecraft.world.level.Level l,net.minecraft.core.BlockPos p,net.minecraft.world.level.block.state.BlockState s,T be);}")
    _replace(stubs, "com/hbm/main/NuclearTechMod.java", "public class NuclearTechMod{",
             "public class NuclearTechMod{public static final Logger LOGGER=new Logger();"
             "public static class Logger{public final java.util.List<String> warnings=new java.util.ArrayList<>();"
             "public void warn(String s,Object... a){warnings.add(s);}}")
    # DummyableBlock: the production fillSpace and makeExtra bodies (copied below), the TYPE property and the hooks
    # MachineArcWelderBlock overrides. Placement (setPlacedBy, checkSpace), breaking, shapes and highlights are not modelled.
    dummyable = (source / "com/hbm/blocks/DummyableBlock.java").read_text(encoding="utf-8")
    fill = method_body(dummyable, "protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {", "DummyableBlock")
    extra_body = method_body(dummyable, "public void makeExtra(Level level, BlockPos pos) {", "DummyableBlock")
    stubs["com/hbm/blocks/DummyableBlock.java"] = (
        "package com.hbm.blocks;import com.hbm.handler.MultiblockHandlerXR;import com.mojang.serialization.MapCodec;"
        "import net.minecraft.core.*;import net.minecraft.world.InteractionResult;import net.minecraft.world.entity.player.Player;"
        "import net.minecraft.world.level.Level;import net.minecraft.world.level.block.Block;import net.minecraft.world.level.block.entity.*;"
        "import net.minecraft.world.level.block.state.BlockState;import net.minecraft.world.level.block.state.properties.EnumProperty;"
        "import net.minecraft.world.phys.BlockHitResult;\n"
        "public abstract class DummyableBlock extends Block{public static final Object FACING=new Object();"
        "public static final EnumProperty<DummyBlockType> TYPE=new EnumProperty<>(DummyBlockType.CORE);public static boolean safeRem;"
        "public DummyableBlock(Properties p){}"
        "protected static <B extends Block> MapCodec<B> simpleCodec(java.util.function.Function<Properties,B> f){return new MapCodec<>();}"
        "protected MapCodec<? extends Block> codec(){return null;}public BlockEntity newBlockEntity(BlockPos p,BlockState s){return null;}"
        "public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level l,BlockState s,BlockEntityType<T> t){return null;}"
        "protected InteractionResult useWithoutItem(BlockState s,Level l,BlockPos p,Player pl,BlockHitResult h){return InteractionResult.PASS;}"
        "protected InteractionResult standardOpenBehavior(Level l,BlockPos p,Player pl){return InteractionResult.SUCCESS;}"
        "public abstract int[] getDimensions();public abstract int getOffset();\n"
        "// Production DummyableBlock.java bodies:\n" + fill + "\n" + extra_body + "\n}")
    # The arc welder implements the real IConditionalInvAccess (compiled from production; the Goal 3B stand-in has
    # no default canInsertItem).
    stubs.pop("com/hbm/blockentity/IConditionalInvAccess.java", None)
    return stubs
