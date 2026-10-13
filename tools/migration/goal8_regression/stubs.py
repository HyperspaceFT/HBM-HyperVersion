"""Goal 8 stand-ins: the Goal 7B services plus entity, explosion and anvil plumbing for the Stirling engine."""

import re

from goal7b_regression.stubs import build_stubs as goal7b_stubs


def _require(text, old, label):
    if old not in text:
        raise SystemExit(f"Goal 8 stub anchor missing in {label}: {old[:60]}")
    return text


def _replace(stubs, name, old, new):
    stubs[name] = _require(stubs[name], old, name).replace(old, new)


def _fields(existing, wanted, make):
    """Declarations for the registry names the production source uses that the stand-in does not define yet."""
    return "".join(make(name) for name in sorted(wanted) if not re.search(rf"\b{name}=", existing))


def build_stubs(source):
    stubs = goal7b_stubs(source)
    anvil = (source / "com/hbm/inventory/recipes/anvil/AnvilRecipes.java").read_text(encoding="utf-8")

    # Registry entries of the engine; the sound refs are identities compared by the regression.
    _replace(stubs, "com/hbm/blockentity/NtmBlockEntityTypes.java", "BATTERY_SOCKET=new Ref()",
             "BATTERY_SOCKET=new Ref(),MACHINE_STIRLING=new Ref()")
    _replace(stubs, "com/hbm/registry/NtmSoundEvents.java", "ASSEMBLER_STOP=new Ref()",
             "ASSEMBLER_STOP=new Ref(),WARN_OVERSPEED=new Ref(),UPGRADE_PLUG=new Ref()")
    _replace(stubs, "net/minecraft/sounds/SoundEvents.java", "FIRECHARGE_USE=new Object()",
             "FIRECHARGE_USE=new Object(),ZOMBIE_BREAK_WOODEN_DOOR=new Object()")
    _replace(stubs, "com/hbm/blockentity/LoadedBaseBlockEntity.java", "public void networkPackNT(int ticks){packs++;}",
             "public int packRange;public void networkPackNT(int range){packs++;packRange=range;}")
    _replace(stubs, "net/minecraft/core/Direction.java", "public Direction getClockWise(){",
             "public Direction getCounterClockWise(){return switch(this){case NORTH->WEST;case WEST->SOUTH;case SOUTH->EAST;case EAST->NORTH;default->this;};}"
             "public Direction getClockWise(){")

    # World effects are recorded, not simulated: sounds, VNT explosions and spawned entities.
    _replace(stubs, "net/minecraft/world/level/Level.java",
             "public void playSound(Object p,double x,double y,double z,Object event,Object source,float volume,float pitch){}",
             "public record Sound(Object player,double x,double y,double z,Object event,Object source,float volume,float pitch){}"
             "public final List<Sound> sounds=new ArrayList<>();"
             "public void playSound(Object p,double x,double y,double z,Object event,Object source,float volume,float pitch){"
             "sounds.add(new Sound(p,x,y,z,event,source,volume,pitch));}"
             "public record Blast(Object exploder,double x,double y,double z,float strength,boolean fire,boolean blockDamage){}"
             "public final List<Blast> blasts=new ArrayList<>();"
             "public final List<net.minecraft.world.entity.Entity> added=new ArrayList<>();"
             "public boolean addFreshEntity(net.minecraft.world.entity.Entity e){added.add(e);return true;}")
    _replace(stubs, "net/minecraft/world/level/Level.java",
             "public void playSound(Object p,BlockPos pos,Object event,Object source,float volume,float pitch){}",
             "public void playSound(Object p,BlockPos pos,Object event,Object source,float volume,float pitch){"
             "sounds.add(new Sound(p,pos.getX()+.5,pos.getY()+.5,pos.getZ()+.5,event,source,volume,pitch));}")
    # ExplosionVNT.newExplosion only allocates and processes blocks when isSmoking is set; that flag is the block damage.
    stubs["com/hbm/explosion/vanillant/ExplosionVNT.java"] = (
        "package com.hbm.explosion.vanillant;import net.minecraft.world.level.Level;import net.minecraft.world.entity.Entity;"
        "public class ExplosionVNT{public static void createExplosion(Level l,Entity e,double x,double y,double z,float s,boolean smoking){"
        "newExplosion(l,e,x,y,z,s,false,smoking);}"
        "public static void newExplosion(Level l,Entity e,double x,double y,double z,float s,boolean fire,boolean smoking){"
        "l.blasts.add(new Level.Blast(e,x,y,z,s,fire,smoking));}}")
    _replace(stubs, "net/minecraft/world/level/block/state/BlockState.java", "public boolean isAir(){return true;}",
             "public boolean isAir(){return true;}public float resistance;"
             "public float getExplosionResistance(net.minecraft.world.level.Level l,BlockPos p,Object explosion){return resistance;}")
    stubs["net/neoforged/neoforge/network/PacketDistributor.java"] = (
        "package net.neoforged.neoforge.network;import java.util.*;public class PacketDistributor{"
        "public record Sent(Object level,Object except,double x,double y,double z,double range,Object payload){}"
        "public static final List<Sent> sent=new ArrayList<>();"
        "public static void sendToPlayersNear(Object a,Object b,double x,double y,double z,double range,Object packet){sent.add(new Sent(a,b,x,y,z,range,packet));}"
        "public static void sendToPlayer(Object player,Object packet){}}")
    stubs["com/hbm/network/toclient/AuxParticle.java"] = (
        "package com.hbm.network.toclient;public class AuxParticle{public final Object tag;public final double x,y,z;"
        "public AuxParticle(Object t,double x,double y,double z){tag=t;this.x=x;this.y=y;this.z=z;}}")

    # Vec3 needs the public x/y/z fields StrayCog reads; the record accessors stay for older callers.
    stubs["net/minecraft/world/phys/Vec3.java"] = (
        "package net.minecraft.world.phys;public class Vec3{public static final Vec3 ZERO=new Vec3(0,0,0);public final double x,y,z;"
        "public Vec3(double x,double y,double z){this.x=x;this.y=y;this.z=z;}public double x(){return x;}public double y(){return y;}public double z(){return z;}"
        "public double length(){return Math.sqrt(x*x+y*y+z*z);}public Vec3 scale(double f){return new Vec3(x*f,y*f,z*f);}"
        "public boolean equals(Object o){return o instanceof Vec3 v&&v.x==x&&v.y==y&&v.z==z;}public int hashCode(){return java.util.Objects.hash(x,y,z);}"
        "public String toString(){return \"(\"+x+\", \"+y+\", \"+z+\")\";}}")
    stubs["net/minecraft/world/phys/EntityHitResult.java"] = (
        "package net.minecraft.world.phys;import net.minecraft.world.entity.Entity;public class EntityHitResult{private final Entity e;"
        "public EntityHitResult(Entity e){this.e=e;}public Entity getEntity(){return e;}}")
    stubs["net/minecraft/world/phys/BlockHitResult.java"] = (
        "package net.minecraft.world.phys;import net.minecraft.core.*;public class BlockHitResult{private final Vec3 at;private final Direction d;private final BlockPos p;"
        "public BlockHitResult(Vec3 at,Direction d,BlockPos p,boolean inside){this.at=at;this.d=d;this.p=p;}public Vec3 getLocation(){return at;}"
        "public Direction getDirection(){return d;}public BlockPos getBlockPos(){return p;}}")

    # Entities: identity, position, motion, synched data and damage plumbing only; no ray tracing or physics.
    stubs["net/minecraft/world/entity/Entity.java"] = (
        "package net.minecraft.world.entity;import net.minecraft.world.level.Level;import net.minecraft.world.phys.Vec3;import net.minecraft.nbt.CompoundTag;"
        "import net.minecraft.network.syncher.SynchedEntityData;import net.minecraft.world.*;import net.minecraft.world.damagesource.*;"
        "public class Entity{private static int ids;private final int id=++ids;public Level level;public final net.minecraft.util.RandomSource random=net.minecraft.util.RandomSource.create();"
        "public int tickCount,baseTicks;public float health=20F;protected final SynchedEntityData entityData;private double px,py,pz;private Vec3 motion=Vec3.ZERO;private boolean removed;"
        "public Entity(){SynchedEntityData.Builder b=new SynchedEntityData.Builder();defineSynchedData(b);entityData=b.build();}"
        "public Entity(EntityType<?> type,Level level){this();this.level=level;}protected void defineSynchedData(SynchedEntityData.Builder b){}"
        "public int getId(){return id;}public void setPos(double x,double y,double z){px=x;py=y;pz=z;}public void setPos(Vec3 v){setPos(v.x,v.y,v.z);}public double getX(){return px;}public double getY(){return py;}public double getZ(){return pz;}"
        "public Vec3 position(){return new Vec3(px,py,pz);}public Vec3 getDeltaMovement(){return motion;}public void setDeltaMovement(Vec3 v){motion=v;}"
        "public void setDeltaMovement(double x,double y,double z){motion=new Vec3(x,y,z);}public boolean isRemoved(){return removed;}public void discard(){removed=true;}"
        "public boolean isAlive(){return !removed&&health>0;}public float getBbHeight(){return 1F;}public DamageSources damageSources(){return new DamageSources();}"
        "public boolean hurt(DamageSource s,float amount){return false;}public InteractionResult interact(net.minecraft.world.entity.player.Player p,InteractionHand h){return InteractionResult.PASS;}"
        "public boolean isPickable(){return false;}public void tick(){baseTick();}public void baseTick(){baseTicks++;}public boolean shouldRenderAtSqrDistance(double d){return false;}"
        "protected void addAdditionalSaveData(CompoundTag t){}protected void readAdditionalSaveData(CompoundTag t){}}")
    stubs["net/minecraft/world/entity/EntityType.java"] = (
        "package net.minecraft.world.entity;public class EntityType<T extends Entity>{}")
    _replace(stubs, "net/minecraft/world/entity/LivingEntity.java", "public class LivingEntity {",
             "public class LivingEntity extends Entity {")
    stubs["net/minecraft/world/damagesource/DamageSource.java"] = (
        "package net.minecraft.world.damagesource;public record DamageSource(Object type){}")
    stubs["net/minecraft/world/damagesource/DamageSources.java"] = (
        "package net.minecraft.world.damagesource;public class DamageSources{public DamageSource source(Object key){return new DamageSource(key);}}")
    stubs["com/hbm/registry/NtmDamageTypes.java"] = (
        "package com.hbm.registry;public class NtmDamageTypes{public static final Object RUBBLE=\"hbmsntm:rubble\";}")
    stubs["net/minecraft/world/InteractionResult.java"] = (
        "package net.minecraft.world;public enum InteractionResult{SUCCESS,CONSUME,PASS,FAIL;"
        "public static InteractionResult sidedSuccess(boolean client){return client?SUCCESS:CONSUME;}}")
    stubs["net/minecraft/network/syncher/EntityDataAccessor.java"] = (
        "package net.minecraft.network.syncher;public class EntityDataAccessor<T>{}")
    stubs["net/minecraft/network/syncher/EntityDataSerializer.java"] = (
        "package net.minecraft.network.syncher;public class EntityDataSerializer<T>{}")
    stubs["net/minecraft/network/syncher/EntityDataSerializers.java"] = (
        "package net.minecraft.network.syncher;public class EntityDataSerializers{public static final EntityDataSerializer<Integer> INT=new EntityDataSerializer<>();}")
    stubs["net/minecraft/network/syncher/SynchedEntityData.java"] = (
        "package net.minecraft.network.syncher;import java.util.*;public class SynchedEntityData{private final Map<EntityDataAccessor<?>,Object> values;"
        "private SynchedEntityData(Map<EntityDataAccessor<?>,Object> v){values=v;}"
        "public static <T> EntityDataAccessor<T> defineId(Class<?> owner,EntityDataSerializer<T> s){return new EntityDataAccessor<>();}"
        "@SuppressWarnings(\"unchecked\")public <T> T get(EntityDataAccessor<T> a){if(!values.containsKey(a))throw new IllegalStateException(\"undefined data\");return (T)values.get(a);}"
        "public <T> void set(EntityDataAccessor<T> a,T v){if(!values.containsKey(a))throw new IllegalStateException(\"undefined data\");values.put(a,v);}"
        "public static class Builder{private final Map<EntityDataAccessor<?>,Object> m=new HashMap<>();"
        "public <T> Builder define(EntityDataAccessor<T> a,T v){m.put(a,v);return this;}public SynchedEntityData build(){return new SynchedEntityData(m);}}}")
    stubs["com/hbm/entity/NtmEntityTypes.java"] = (
        "package com.hbm.entity;public class NtmEntityTypes{public static final Holder<net.minecraft.world.entity.EntityType<com.hbm.entity.projectile.StrayCog>> "
        "STRAY_COG=new Holder<>(new net.minecraft.world.entity.EntityType<>());public static class Holder<T>{private final T v;Holder(T v){this.v=v;}public T get(){return v;}}}")
    # ProjectileNT's ray tracing and drag are replaced: tick() only counts the flight step and applies StrayCog's gravity hook.
    stubs["com/hbm/entity/projectile/ProjectileNT.java"] = (
        "package com.hbm.entity.projectile;import net.minecraft.world.entity.*;import net.minecraft.world.level.Level;import net.minecraft.world.phys.*;"
        "public abstract class ProjectileNT extends Entity{public int flightTicks;protected ProjectileNT(EntityType<? extends ProjectileNT> t,Level l){super(t,l);}"
        "public void tick(){flightTicks++;super.tick();Vec3 v=getDeltaMovement();setDeltaMovement(v.x,v.y-getDefaultGravity(),v.z);}"
        "protected double getDefaultGravity(){return 0.03;}public boolean shouldRenderAtSqrDistance(double d){return d<4096;}"
        "protected void onHitEntity(EntityHitResult r){}protected void onHitBlock(BlockHitResult r){}}")
    _replace(stubs, "net/minecraft/world/entity/player/Inventory.java", "public class Inventory implements Container{",
             "public class Inventory implements Container{public boolean rejectAdd;public int changed;public void setChanged(){changed++;}"
             "public boolean add(ItemStack s){if(rejectAdd||s.isEmpty())return false;for(int i=0;i<items.size();i++)if(items.get(i).isEmpty()){"
             "items.set(i,s.copy());s.setCount(0);return true;}return false;}")
    _replace(stubs, "net/minecraft/world/entity/player/Player.java", "public Object containerMenu;",
             "public net.minecraft.world.inventory.AbstractContainerMenu containerMenu;public int dropped;"
             "public net.minecraft.util.RandomSource getRandom(){return random;}public void drop(ItemStack s,boolean r){dropped+=s.getCount();}")
    _replace(stubs, "net/minecraft/world/inventory/AbstractContainerMenu.java", "public void removed(Player p){}",
             "public void removed(Player p){}public int broadcasts;public void broadcastChanges(){broadcasts++;}")

    # Anvil recipes: the Goal 3A/5A anvil stand-ins merged into this chain, with production ComparableStack meta rules.
    _replace(stubs, "net/minecraft/tags/ItemTags.java", "public static final String LOGS=\"logs\",SAPLINGS=\"saplings\";",
             "public static final String LOGS=\"logs\",SAPLINGS=\"saplings\",PLANKS=\"planks\";"
             "public static Object create(net.minecraft.resources.ResourceLocation id){return id.n()+\":\"+id.p();}")
    _replace(stubs, "net/minecraft/world/item/Items.java", "SUGAR=new Item(\"minecraft:sugar\");",
             "SUGAR=new Item(\"minecraft:sugar\"),GOLD_INGOT=new Item(\"minecraft:gold_ingot\"),"
             "COPPER_INGOT=new Item(\"minecraft:copper_ingot\"),BRICK=new Item(\"minecraft:brick\");")
    _replace(stubs, "net/minecraft/world/level/block/Blocks.java", "BRICKS=new Block(\"bricks\");",
             "BRICKS=new Block(\"bricks\"),STONE_BRICKS=new Block(\"stone_bricks\"),FURNACE=new Block(\"furnace\");")
    stubs["com/hbm/inventory/RecipesCommon.java"] = (
        "package com.hbm.inventory;import java.util.*;import net.minecraft.world.item.*;import net.minecraft.world.level.ItemLike;"
        "public class RecipesCommon{public static abstract class AStack{public int stacksize=1;public abstract boolean matchesRecipe(ItemStack s,boolean ignoreSize);"
        "public List<ItemStack> extractForJEI(){return List.of();}}"
        # Same rules as production RecipesCommon.ComparableStack: (item) and (item,count) are meta wildcards.
        "public static class ComparableStack extends AStack{public final Item item;public int meta=MetaHelper.WILDCARD_VALUE;"
        "public ComparableStack(ItemLike i){item=i.asItem();}public ComparableStack(ItemLike i,int n){this(i);stacksize=n;}"
        "public ComparableStack(ItemLike i,int n,int m){this(i,n);meta=m;}"
        "public boolean matchesRecipe(ItemStack s,boolean ignoreSize){if(s==null||s.getItem()!=item)return false;"
        "if(meta!=MetaHelper.WILDCARD_VALUE&&MetaHelper.getMeta(s)!=meta)return false;return ignoreSize||s.getCount()>=stacksize;}"
        "public ItemStack toStack(){return MetaHelper.newStack(item,stacksize,meta);}public List<ItemStack> extractForJEI(){return List.of(toStack());}}"
        "public static class TagStack extends AStack{public final Object tag;public TagStack(Object t){tag=t;}public TagStack(Object t,int n){tag=t;stacksize=n;}"
        "public boolean matchesRecipe(ItemStack s,boolean ignoreSize){return !s.isEmpty()&&s.is(tag)&&(ignoreSize||s.getCount()>=stacksize);}}}")
    items = stubs["com/hbm/items/NtmItems.java"]
    wanted = set(re.findall(r"NtmItems\.([A-Z][A-Z_0-9]+)", anvil)) | {"CAST_PLATE", "GEAR_LARGE"}
    items = _require(items, "FLUID_IDENTIFIER_MULTI=", "NtmItems").replace(
        "FLUID_IDENTIFIER_MULTI=",
        _fields(items, wanted, lambda n: f'{n}=new Ref("hbmsntm:{n.lower()}"),') + "FLUID_IDENTIFIER_MULTI=", 1)
    items = _require(items, "public static class Ref{private final Item item;", "NtmItems").replace(
        "public static class Ref{private final Item item;",
        "public static com.hbm.inventory.RecipesCommon.AStack castPlateIngredient(com.hbm.items.CastPlateItem.Type t,int n){"
        "return new com.hbm.inventory.RecipesCommon.ComparableStack(CAST_PLATE.get(),n,t.ordinal());}"
        "public static class Ref implements net.minecraft.world.level.ItemLike{public Item asItem(){return item;}private final Item item;")
    stubs["com/hbm/items/NtmItems.java"] = items
    blocks = stubs["com/hbm/blocks/NtmBlocks.java"]
    anchor = "public static final Ref MACHINE_ASSEMBLY_MACHINE=new Ref(\"MACHINE_ASSEMBLY_MACHINE\");"
    extra = _fields(blocks, set(re.findall(r"NtmBlocks\.([A-Z][A-Z_0-9]+)", anvil)) | {"MACHINE_STIRLING"},
                    lambda n: f'public static final Ref {n}=new Ref("hbmsntm:{n.lower()}");')
    stubs["com/hbm/blocks/NtmBlocks.java"] = _require(blocks, anchor, "NtmBlocks").replace(anchor, anchor + extra)
    stubs["com/hbm/items/BoltItem.java"] = (
        "package com.hbm.items;public class BoltItem{public enum Type{TUNGSTEN(1),STEEL(2);public final int meta;Type(int n){meta=n;}}}")
    # Goal 12A: the desh motor entry names WireDenseItem.Type.GOLD.meta; the production constants and metas, as Goal 10B.
    from goal10b_regression.stubs import meta_enum
    stubs["com/hbm/items/WireDenseItem.java"] = meta_enum(
        (source / "com/hbm/items/WireDenseItem.java").read_text(encoding="utf-8"), "com.hbm.items", "WireDenseItem", "WireDenseItem")
    stubs["com/hbm/blocks/machine/NTMAnvilBlock.java"] = (
        "package com.hbm.blocks.machine;public class NTMAnvilBlock{public enum Variant{IRON,LEAD,STEEL,DESH,FERROURANIUM,SATURNITE,"
        "BISMUTH_BRONZE,ARSENIC_BRONZE,FERRIC_SCHRABIDATE,DINEUTRONIUM,OSMIRIDIUM}}")
    stubs["com/hbm/util/InventoryUtil.java"] = (
        "package com.hbm.util;import java.util.*;import com.hbm.inventory.RecipesCommon.AStack;import net.minecraft.world.entity.player.Player;"
        "public class InventoryUtil{public static boolean doesPlayerHaveAStacks(Player p,List<AStack> s,boolean take){return false;}}")
    stubs["com/hbm/inventory/recipes/anvil/AnvilSmithingRecipe.java"] = (
        "package com.hbm.inventory.recipes.anvil;import com.hbm.inventory.RecipesCommon.AStack;import net.minecraft.world.item.ItemStack;"
        "public class AnvilSmithingRecipe{public AnvilSmithingRecipe(){}public AnvilSmithingRecipe(int tier,ItemStack out,AStack left,AStack right){}}")
    # Goal 17A registers two more mold smithing recipes; like the three before them they are identities here (Goal 19A harness revival).
    for name in ("AnvilSmithingCyanideRecipe", "AnvilSmithingRenameRecipe", "AnvilSmithingCastMoldRecipe",
                 "AnvilSmithingIngotMoldRecipe", "AnvilSmithingBladeMoldRecipe"):
        stubs[f"com/hbm/inventory/recipes/anvil/{name}.java"] = (
            f"package com.hbm.inventory.recipes.anvil;public class {name} extends AnvilSmithingRecipe{{}}")
    return stubs
