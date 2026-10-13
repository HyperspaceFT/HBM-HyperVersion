"""Goal 9A stand-ins: the Goal 8 services plus the vanilla item component model, boiler plumbing and heating traits."""

import re

from goal8_regression.stubs import build_stubs as goal8_stubs


def _require(text, old, label):
    if old not in text:
        raise SystemExit(f"Goal 9A stub anchor missing in {label}: {old[:60]}")
    return text


def _replace(stubs, name, old, new):
    stubs[name] = _require(stubs[name], old, name).replace(old, new)


def heatable_traits(fluids_source):
    """FT_Heatable definitions of production Fluids.java as (fluid, [(type, efficiency)], [(heat, req, product, prod)])."""
    constants = dict(re.findall(r"double (\w+) = ([\d.]+)D;", fluids_source))
    found = []
    for match in re.finditer(r"(\w+)\.addTraits\(new FT_Heatable\(\)((?:\s*\.(?:setEff|addStep)\([^)]*\))+)", fluids_source):
        effs = [(kind, float(constants.get(value, value.rstrip("D"))))
                for kind, value in re.findall(r"setEff\(HeatingType\.(\w+), ([\w.]+)\)", match.group(2))]
        steps = [(int(h), int(r), product, int(p)) for h, r, product, p in re.findall(r"addStep\((\d+), (\d+), (\w+), (\d+)\)", match.group(2))]
        found.append((match.group(1), effs, steps))
    if len(found) != fluids_source.count("new FT_Heatable()") or not found:
        raise SystemExit("Goal 9A: could not parse every FT_Heatable definition in Fluids.java")
    return found


def build_stubs(source):
    stubs = goal8_stubs(source)
    fluids_source = (source / "com/hbm/inventory/fluid/Fluids.java").read_text(encoding="utf-8")

    # ---- Vanilla item components (1.21.1 semantics, see goal9a_regression/README.md) ----------------------------
    # Keys are DataComponentType identities; a stack is the item's prototype (Item.defaults) plus a patch of
    # Optional values. set() drops the patch entry when the value equals the prototype; remove() writes Optional.empty()
    # only when the prototype has the type; applyPatch/fromPatch sanitise the same way; equality compares both.
    stubs["net/minecraft/core/component/DataComponentType.java"] = (
        "package net.minecraft.core.component;public final class DataComponentType<T>{private final String name;"
        "public DataComponentType(String n){name=n;}public String toString(){return name;}}")
    stubs["net/minecraft/core/component/DataComponents.java"] = (
        "package net.minecraft.core.component;public class DataComponents{"
        "public static final DataComponentType<net.minecraft.network.chat.Component> CUSTOM_NAME=new DataComponentType<>(\"minecraft:custom_name\");"
        "public static final DataComponentType<Object> LORE=new DataComponentType<>(\"minecraft:lore\");"
        "public static final DataComponentType<net.minecraft.world.item.alchemy.PotionContents> POTION_CONTENTS=new DataComponentType<>(\"minecraft:potion_contents\");}")
    stubs["net/minecraft/core/component/DataComponentPatch.java"] = (
        "package net.minecraft.core.component;import java.util.*;public final class DataComponentPatch{"
        "public static final DataComponentPatch EMPTY=new DataComponentPatch(Map.of());public final Map<Object,Optional<?>> map;"
        "public DataComponentPatch(Map<Object,Optional<?>> m){map=Collections.unmodifiableMap(new LinkedHashMap<>(m));}"
        "@SuppressWarnings({\"unchecked\",\"rawtypes\"})public Set<Map.Entry<DataComponentType<?>,Optional<?>>> entrySet(){return (Set)map.entrySet();}"
        "public boolean isEmpty(){return map.isEmpty();}public int size(){return map.size();}"
        "public boolean equals(Object o){return o instanceof DataComponentPatch p&&map.equals(p.map);}public int hashCode(){return map.hashCode();}"
        "public String toString(){return map.toString();}}")
    stubs["net/minecraft/core/component/PatchedDataComponentMap.java"] = (
        "package net.minecraft.core.component;import java.util.*;public final class PatchedDataComponentMap{"
        "private final Map<Object,Object> prototype;private final Map<Object,Optional<?>> patch=new LinkedHashMap<>();"
        "public PatchedDataComponentMap(Map<Object,Object> prototype){this.prototype=prototype;}"
        "public static PatchedDataComponentMap fromPatch(Map<Object,Object> prototype,DataComponentPatch p){PatchedDataComponentMap m=new PatchedDataComponentMap(prototype);m.applyPatch(p);return m;}"
        "public Object get(Object type){Optional<?> o=patch.get(type);return o!=null?o.orElse(null):prototype.get(type);}"
        "public boolean has(Object type){return get(type)!=null;}"
        "public Object set(Object type,Object value){Object old=get(type);if(Objects.equals(value,prototype.get(type)))patch.remove(type);else patch.put(type,Optional.ofNullable(value));return old;}"
        "public Object remove(Object type){Object old=get(type);if(prototype.get(type)!=null)patch.put(type,Optional.empty());else patch.remove(type);return old;}"
        "public void applyPatch(DataComponentPatch p){for(Map.Entry<Object,Optional<?>> e:p.map.entrySet()){Object proto=prototype.get(e.getKey());"
        "if(e.getValue().isPresent()){if(e.getValue().get().equals(proto))patch.remove(e.getKey());else patch.put(e.getKey(),e.getValue());}"
        "else if(proto!=null)patch.put(e.getKey(),Optional.empty());else patch.remove(e.getKey());}}"
        "public DataComponentPatch asPatch(){return patch.isEmpty()?DataComponentPatch.EMPTY:new DataComponentPatch(patch);}"
        "public boolean isPatchEmpty(){return patch.isEmpty();}public PatchedDataComponentMap copy(){PatchedDataComponentMap m=new PatchedDataComponentMap(prototype);m.patch.putAll(patch);return m;}"
        "public boolean equals(Object o){return o instanceof PatchedDataComponentMap m&&prototype.equals(m.prototype)&&patch.equals(m.patch);}"
        "public int hashCode(){return prototype.hashCode()*31+patch.hashCode();}public String toString(){return prototype+\"+\"+patch;}}")
    # The rest of the ItemStack surface is the Goal 8 stand-in; only the component storage follows the vanilla model.
    # transmuteCopy carries the source patch onto the new item's prototype (ItemStack.transmuteCopyIgnoreEmpty).
    stubs["net/minecraft/world/item/ItemStack.java"] = """package net.minecraft.world.item;import java.util.*;import net.minecraft.world.level.ItemLike;import net.minecraft.network.chat.Component;import net.minecraft.core.component.*;
public class ItemStack{public static final ItemStack EMPTY=new ItemStack((ItemLike)null,0);private final Item item;private int count,damage;public net.minecraft.nbt.CompoundTag customTag;private final PatchedDataComponentMap components;
public ItemStack(ItemLike i){this(i,1);}public ItemStack(ItemLike i,int n){item=i==null?null:i.asItem();count=n;components=new PatchedDataComponentMap(item==null?Map.of():item.defaults);}
private ItemStack(Item i,int n,PatchedDataComponentMap c){item=i;count=n;components=c;}
public Item getItem(){return item;}public int getCount(){return isEmpty()?0:count;}public void setCount(int n){count=n;}public boolean isEmpty(){return item==null||count<=0;}
public boolean is(Item i){return item==i;}public boolean is(Object tag){return tag instanceof String s&&item!=null&&(item.tags.contains(s)||s.equals("logs")&&item.id.contains("log")||s.equals("saplings")&&item.id.contains("sapling"));}
public void grow(int n){count+=n;}public void shrink(int n){count=Math.max(0,count-n);}
public ItemStack copy(){if(isEmpty())return EMPTY;ItemStack s=new ItemStack(item,count,components.copy());s.damage=damage;s.customTag=customTag==null?null:customTag.copy();return s;}
public ItemStack copyWithCount(int n){if(isEmpty())return EMPTY;ItemStack s=copy();s.count=n;return s;}
public ItemStack transmuteCopy(ItemLike replacement,int n){if(isEmpty())return EMPTY;Item r=replacement.asItem();ItemStack s=new ItemStack(r,n,PatchedDataComponentMap.fromPatch(r.defaults,components.asPatch()));s.customTag=customTag==null?null:customTag.copy();return s;}
public ItemStack transmuteCopy(Item replacement,int n){return transmuteCopy((ItemLike)replacement,n);}
public int getMaxStackSize(){return item==null?64:item.maxStack;}public void limitSize(int n){count=Math.min(count,n);}public boolean isDamageableItem(){return getMaxDamage()>0;}public int getMaxDamage(){return item==null?0:item.maxDamage;}public int getDamageValue(){return damage;}public void setDamageValue(int n){damage=n;}public int getBurnTime(Object context){return item==null?0:item.burn;}
public boolean hasCraftingRemainingItem(){return item!=null&&item.remainder!=null;}public ItemStack getCraftingRemainingItem(){return hasCraftingRemainingItem()?new ItemStack(item.remainder):EMPTY;}
@SuppressWarnings("unchecked")public <T> T set(Object key,T value){return (T)components.set(key,value);}@SuppressWarnings("unchecked")public <T> T get(Object key){return (T)components.get(key);}
@SuppressWarnings("unchecked")public <T> T getOrDefault(Object key,T fallback){Object v=components.get(key);return v==null?fallback:(T)v;}public boolean has(Object key){return components.has(key);}
@SuppressWarnings("unchecked")public <T> T remove(Object key){return (T)components.remove(key);}
public DataComponentPatch getComponentsPatch(){return isEmpty()?DataComponentPatch.EMPTY:components.asPatch();}public boolean isComponentsPatchEmpty(){return isEmpty()||components.isPatchEmpty();}
public void applyComponents(DataComponentPatch patch){components.applyPatch(patch);}
public Component getHoverName(){Object v=components.get(DataComponents.CUSTOM_NAME);return v instanceof Component c?c:Component.literal(item==null?"empty":item.id);}
public String component(){return "";}public ItemStack component(String s){return this;}
public static boolean isSameItemSameComponents(ItemStack a,ItemStack b){if(a.getItem()!=b.getItem())return false;return a.isEmpty()&&b.isEmpty()||Objects.equals(a.components,b.components);}
public String toString(){return getCount()+" "+(item==null?"air":item.id)+(components.isPatchEmpty()?"":" "+components);}}"""
    _replace(stubs, "net/minecraft/world/item/Item.java", "public final List<String> tags=new ArrayList<>();",
             "public final List<String> tags=new ArrayList<>();public final Map<Object,Object> defaults=new HashMap<>();")
    stubs["com/hbm/items/component/NtmDataComponents.java"] = (
        "package com.hbm.items.component;import net.minecraft.core.component.DataComponentType;public class NtmDataComponents{"
        "public static final Ref<Integer> META=new Ref<>(\"hbmsntm:meta\");public static class Ref<T>{private final DataComponentType<T> type;"
        "Ref(String n){type=new DataComponentType<>(n);}public DataComponentType<T> get(){return type;}}}")
    stubs["net/minecraft/core/Holder.java"] = (
        "package net.minecraft.core;public interface Holder<T>{T value();record Direct<T>(T value) implements Holder<T>{}}")
    stubs["net/minecraft/world/item/alchemy/Potion.java"] = (
        "package net.minecraft.world.item.alchemy;public final class Potion{public final String name;public Potion(String n){name=n;}public String toString(){return name;}}")
    stubs["net/minecraft/world/item/alchemy/Potions.java"] = (
        "package net.minecraft.world.item.alchemy;import net.minecraft.core.Holder;public class Potions{"
        "public static final Holder<Potion> WATER=new Holder.Direct<>(new Potion(\"water\")),AWKWARD=new Holder.Direct<>(new Potion(\"awkward\")),"
        "HEALING=new Holder.Direct<>(new Potion(\"healing\"));}")
    # A record, as in 1.21.1: value equality on the potion holder, colour and custom effects.
    stubs["net/minecraft/world/item/alchemy/PotionContents.java"] = (
        "package net.minecraft.world.item.alchemy;import java.util.*;import net.minecraft.core.Holder;import net.minecraft.core.component.DataComponents;import net.minecraft.world.item.*;"
        "public record PotionContents(Optional<Holder<Potion>> potion,Optional<Integer> customColor,List<Object> customEffects){"
        "public static final PotionContents EMPTY=new PotionContents(Optional.empty(),Optional.empty(),List.of());"
        "public PotionContents(Holder<Potion> p){this(Optional.of(p),Optional.empty(),List.of());}"
        "public static ItemStack createItemStack(Item item,Holder<Potion> potion){ItemStack s=new ItemStack(item);s.set(DataComponents.POTION_CONTENTS,new PotionContents(potion));return s;}}")
    # Items.java:1214-1215 and 1366-1369: bucket 16, water bucket 1 (remainder bucket), potion 1 with the default
    # POTION_CONTENTS = EMPTY, glass bottle 64 without that default.
    _replace(stubs, "net/minecraft/world/item/Items.java",
             "public static final Item WATER_BUCKET=new Item(\"minecraft:water_bucket\"),BUCKET=new Item(\"minecraft:bucket\"),"
             "GLASS_BOTTLE=new Item(\"minecraft:glass_bottle\"),POTION=new Item(\"minecraft:potion\");",
             "public static final Item BUCKET=new Item(\"minecraft:bucket\",16,0),WATER_BUCKET=new Item(\"minecraft:water_bucket\",1,0,BUCKET),"
             "GLASS_BOTTLE=new Item(\"minecraft:glass_bottle\",64,0),POTION=new Item(\"minecraft:potion\",1,0);"
             "static{POTION.defaults.put(net.minecraft.core.component.DataComponents.POTION_CONTENTS,net.minecraft.world.item.alchemy.PotionContents.EMPTY);}")

    # ---- Boiler plumbing -----------------------------------------------------------------------------------------
    _replace(stubs, "com/hbm/blockentity/NtmBlockEntityTypes.java", "BATTERY_SOCKET=new Ref()",
             "BATTERY_SOCKET=new Ref(),HEAT_BOILER=new Ref(),MACHINE_INDUSTRIAL_BOILER=new Ref()")
    _replace(stubs, "com/hbm/registry/NtmSoundEvents.java", "ASSEMBLER_STOP=new Ref()",
             "ASSEMBLER_STOP=new Ref(),BOILER=new Ref(),BOILER_GROAN=new Ref()")
    _replace(stubs, "net/minecraft/core/BlockPos.java", "public BlockPos above(int n){",
             "public BlockPos above(){return above(1);}public BlockPos above(int n){")
    stubs["com/hbm/blocks/DummyableBlock.java"] = (
        "package com.hbm.blocks;public class DummyableBlock{public static final Object FACING=new Object();public static boolean safeRem;}")
    # Block removal is recorded together with DummyableBlock.safeRem at that moment; the block and its entity go.
    _replace(stubs, "net/minecraft/world/level/Level.java", "public boolean removeBlock(BlockPos p,boolean update){return true;}",
             "public record Removal(BlockPos pos,boolean safeRem){}public final List<Removal> removals=new ArrayList<>();"
             "public boolean removeBlock(BlockPos p,boolean update){removals.add(new Removal(p,com.hbm.blocks.DummyableBlock.safeRem));"
             "states.remove(p);BlockEntity be=entities.remove(p);if(be!=null)be.setRemoved();return true;}"
             "public final List<com.hbm.explosion.vanillant.ExplosionVNT> vnts=new ArrayList<>();")
    # ExplosionVNT records what the production builder receives; explode() stores it with the safeRem state and
    # simulates nothing. The static helpers keep the Goal 8 Blast record for the Stirling and stray cog code.
    stubs["com/hbm/explosion/vanillant/ExplosionVNT.java"] = (
        "package com.hbm.explosion.vanillant;import com.hbm.explosion.vanillant.interfaces.*;import net.minecraft.world.level.Level;import net.minecraft.world.entity.Entity;"
        "public class ExplosionVNT{public final Level level;public final double x,y,z;public final float size;public final Entity exploder;"
        "public IBlockAllocator blockAllocator;public IEntityProcessor entityProcessor;public IBlockProcessor blockProcessor;public IExplosionSFX[] sfx;"
        "public int explodeCalls;public boolean safeRemAtExplode;"
        "public ExplosionVNT(Level l,double x,double y,double z,float s){this(l,x,y,z,s,null);}"
        "public ExplosionVNT(Level l,double x,double y,double z,float s,Entity e){level=l;this.x=x;this.y=y;this.z=z;size=s;exploder=e;}"
        "public void explode(){explodeCalls++;safeRemAtExplode=com.hbm.blocks.DummyableBlock.safeRem;level.vnts.add(this);}"
        "public ExplosionVNT setBlockAllocator(IBlockAllocator a){blockAllocator=a;return this;}"
        "public ExplosionVNT setEntityProcessor(IEntityProcessor p){entityProcessor=p;return this;}"
        "public ExplosionVNT setBlockProcessor(IBlockProcessor p){blockProcessor=p;return this;}"
        "public ExplosionVNT setSFX(IExplosionSFX... s){sfx=s;return this;}"
        "public static void createExplosion(Level l,Entity e,double x,double y,double z,float s,boolean smoking){newExplosion(l,e,x,y,z,s,false,smoking);}"
        "public static void newExplosion(Level l,Entity e,double x,double y,double z,float s,boolean fire,boolean smoking){"
        "l.blasts.add(new Level.Blast(e,x,y,z,s,fire,smoking));}}")
    for name in ("IBlockAllocator", "IEntityProcessor", "IBlockProcessor", "IExplosionSFX"):
        stubs[f"com/hbm/explosion/vanillant/interfaces/{name}.java"] = (
            f"package com.hbm.explosion.vanillant.interfaces;public interface {name}{{}}")
    stubs["com/hbm/explosion/vanillant/standard/EntityProcessorStandard.java"] = (
        "package com.hbm.explosion.vanillant.standard;public class EntityProcessorStandard implements com.hbm.explosion.vanillant.interfaces.IEntityProcessor{"
        "public Float rangeMod;public EntityProcessorStandard withRangeMod(float mod){rangeMod=mod;return this;}}")
    stubs["com/hbm/explosion/vanillant/standard/ExplosionEffectStandard.java"] = (
        "package com.hbm.explosion.vanillant.standard;public class ExplosionEffectStandard implements com.hbm.explosion.vanillant.interfaces.IExplosionSFX{}")

    # ---- Heating traits: production FT_Heatable on a minimal FluidTrait/gson surface -------------------------------
    stubs["com/hbm/inventory/fluid/trait/FluidTrait.java"] = (
        "package com.hbm.inventory.fluid.trait;import java.util.List;import net.minecraft.network.chat.Component;public class FluidTrait{"
        "public void addInfo(List<Component> info){}public void addInfoHidden(List<Component> info){}"
        "public void serializeJSON(com.google.gson.stream.JsonWriter w)throws java.io.IOException{}public void deserializeJSON(com.google.gson.JsonObject o){}"
        # Goal 19A: the corroded barrel's leak names the release type and dispatcher; no corroded barrel leaks in this world.
        "public enum FluidReleaseType{VOID,BURN,SPILL}"
        "public static void onRelease(net.minecraft.world.level.Level l,net.minecraft.core.BlockPos p,com.hbm.inventory.fluid.FluidType t,"
        "com.hbm.inventory.fluid.tank.FluidTank tank,FluidReleaseType r,int mB){}}")
    stubs["com/google/gson/JsonElement.java"] = (
        "package com.google.gson;public class JsonElement{public JsonArray getAsJsonArray(){return null;}public JsonObject getAsJsonObject(){return null;}"
        "public int getAsInt(){return 0;}public double getAsDouble(){return 0;}public String getAsString(){return \"\";}}")
    stubs["com/google/gson/JsonObject.java"] = (
        "package com.google.gson;public class JsonObject extends JsonElement{public JsonElement get(String k){return null;}public boolean has(String k){return false;}}")
    stubs["com/google/gson/JsonArray.java"] = (
        "package com.google.gson;public class JsonArray extends JsonElement{public int size(){return 0;}public JsonElement get(int i){return null;}}")
    stubs["com/google/gson/stream/JsonWriter.java"] = (
        "package com.google.gson.stream;public class JsonWriter{public JsonWriter name(String n){return this;}public JsonWriter value(String v){return this;}"
        "public JsonWriter value(long v){return this;}public JsonWriter value(double v){return this;}public JsonWriter value(Number v){return this;}"
        "public JsonWriter beginArray(){return this;}public JsonWriter endArray(){return this;}public JsonWriter beginObject(){return this;}public JsonWriter endObject(){return this;}}")
    _replace(stubs, "com/hbm/inventory/fluid/FluidType.java", "public int getTint(){return 0;}",
             "public boolean hasTrait(Class<?> c){return traits.containsKey(c);}public FluidType addTraits(Object... ts){for(Object t:ts)traits.put(t.getClass(),t);return this;}"
             "public String getInternalName(){return getUnlocalizedName();}public int getTint(){return 0;}")

    # Fluids: the Goal 8 identities keep their IDs and traits; the heatable fluids and their products are appended and
    # get the FT_Heatable traits parsed from production Fluids.java (water: BOILER 1.0, 200 TU + 1 mB -> 100 mB steam).
    fluids = stubs["com/hbm/inventory/fluid/Fluids.java"]
    existing = [(name, int(i), lead == "true", none == "true")
                for name, i, lead, none in re.findall(r"(\w+)=new FluidType\((\d+),(true|false),(true|false)\)", fluids)]
    statics = re.search(r"static\{(.*?)\}public static FluidType\[\] getAll", fluids).group(1)
    names = [name for name, *_ in existing]
    traits = heatable_traits(fluids_source)
    for fluid, _, steps in traits:
        for name in [fluid] + [product for *_, product, _ in steps]:
            if name not in names:
                names.append(name)
                existing.append((name, len(existing), False, False))
    heat = "".join(
        f"{fluid}.addTraits(new com.hbm.inventory.fluid.trait.FT_Heatable()"
        + "".join(f".setEff(com.hbm.inventory.fluid.trait.FT_Heatable.HeatingType.{kind},{eff}D)" for kind, eff in effs)
        + "".join(f".addStep({h},{r},{product},{p})" for h, r, product, p in steps) + ");"
        for fluid, effs, steps in traits)
    stubs["com/hbm/inventory/fluid/Fluids.java"] = (
        "package com.hbm.inventory.fluid;public class Fluids{public static final FluidType "
        + ",".join(f"{name}=new FluidType({i},{str(lead).lower()},{str(none).lower()})" for name, i, lead, none in existing)
        + ";static{" + statics + heat + "}public static FluidType[] getAll(){return new FluidType[]{" + ",".join(names) + "};}"
        + "public static FluidType fromID(int id){return switch(id){" + "".join(f"case {i}->{name};" for name, i, *_ in existing)
        + "default->NONE;};}public static FluidType fromNameCompat(String s){return NONE;}public static FluidType fromName(String s){return NONE;}}")
    return stubs
