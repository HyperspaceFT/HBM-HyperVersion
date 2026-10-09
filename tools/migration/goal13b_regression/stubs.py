"""Goal 13B stand-ins: the Goal 13A machine and recipe worlds plus what the arc furnace, the silicon electrodes' wear component, the arc
furnace table, the silicon billet press entry and the chip chain need.

Machine world (build_stubs): the Goal 13A machine world (goal13a_regression/stubs.py: the Goal 12B machine world with the production
assembler, heaters and blueprint items) extended with the production MachineArcFurnaceBlock, MachineArcFurnaceBlockEntity,
MachineArcFurnaceMenu, ArcElectrodeItem and ArcFurnaceRecipes:

* registry entries: the four electrodes in NtmItems are production ArcElectrodeItems built as NtmItems registers them (the stack size, the
  maximum and the burnt item are read from the NtmItems text, behind a lazy supplier), the burnt items and the silicon items stay plain stand-ins, NtmDataComponents gains
  ARC_ELECTRODE_DURABILITY (the other registries derive their entries from the names the sources use);
* the real Minecraft 1.21.1 Mth.hsvToRgb (the stand-in answered 0), read from the NeoForge sources JAR when the stand-ins are built, for
  ArcElectrodeItem.getBarColor;
* Component.translatable keeps its arguments (the wear tooltip line);
* the client branch of the block entity: SoundUtils.playAtVec3 for the block centre, ParticleUtil.addParticle, NbtParticleOptions and
  NtmParticleTypes (recording what is added), Player.distanceToSqr with a position the fixture sets;
* RecipesCommon.ComparableStack with the production makeSingular, equals and hashCode (ArcFurnaceRecipes' de-duplication keys on them).

Recipe world (recipe_stubs): the Goal 13A recipe world (Goal 12B, Goal 11D: real Gson, the production SerializableRecipe, GenericRecipes,
GenericRecipe and the tables) extended with the production ArcFurnaceRecipes and PressRecipes:

* the Goal 3C name-only handler stand-ins of the two tables are dropped (the production classes are compiled);
* RecipesCommon with the production AStack, ComparableStack and TagStack semantics the two tables and the soldering station call
  (mutable meta, makeSingular, matchesRecipe, equals/hashCode, a tag matching through the items' tag lists, tag members fixture-set);
* StampItem with the production StampType enum (read from StampItem.java), and the names the two tables and the fixture use.

See goal13b_regression/README.md for what each stand-in models and what it leaves out.
"""

import re
import zipfile

from goal10b_regression.stubs import method_body
from goal11c_regression.stubs import _declare, _replace, names
from goal13a_regression.stubs import build_stubs as goal13a_stubs, recipe_stubs as goal13a_recipe_stubs

ARC_RECIPES = "com/hbm/inventory/recipes/ArcFurnaceRecipes.java"
PRESS = "com/hbm/inventory/recipes/PressRecipes.java"
ARC_ELECTRODE = "com/hbm/items/machine/ArcElectrodeItem.java"
ARC_BE = "com/hbm/blockentity/machine/MachineArcFurnaceBlockEntity.java"
ARC_BLOCK = "com/hbm/blocks/machine/MachineArcFurnaceBlock.java"
ARC_MENU = "com/hbm/inventory/menus/MachineArcFurnaceMenu.java"
STAMP_ITEM = "com/hbm/items/machine/StampItem.java"
# Production sources the machine world compiles on top of the Goal 13A machine world, and the two tables of the recipe world.
GOAL13B_SOURCES = (ARC_RECIPES, ARC_ELECTRODE, ARC_BE, ARC_BLOCK, ARC_MENU)
GOAL13B_RECIPE_SOURCES = (ARC_RECIPES, PRESS)

NTM_ITEMS = "com/hbm/items/NtmItems.java"
ELECTRODE_PATTERN = (r'(ARC_ELECTRODE_[A-Z]+)\s*=\s*ITEMS\.register\("[a-z_]+",\s*\(\)\s*->\s*new ArcElectrodeItem\(new Item\.Properties\(\)\.stacksTo\((\d+)\),\s*(\d+),\s*NtmItems\.(ARC_ELECTRODE_[A-Z_]+)\)\)')


def electrodes(source):
    """The four electrodes as the production NtmItems registers them: (constant, stack size, maximum durability, burnt constant)."""
    text = (source / NTM_ITEMS).read_text(encoding="utf-8")
    found = [(c, int(stack), int(maximum), burnt) for c, stack, maximum, burnt in re.findall(ELECTRODE_PATTERN, text)]
    if len(found) != 4:
        raise SystemExit(f"Goal 13B: NtmItems registers {len(found)} ArcElectrodeItem constants in the expected form, not 4")
    return found

PARTICLE_STUBS = {
    "com/hbm/particle/vanilla/NbtParticleOptions.java":
        "package com.hbm.particle.vanilla;/** The type token and the data tag of the production class. */public class NbtParticleOptions{public final Object type;public final net.minecraft.nbt.CompoundTag tag;"
        "public NbtParticleOptions(Object type,net.minecraft.nbt.CompoundTag tag){this.type=type;this.tag=tag;}}",
    "com/hbm/particle/NtmParticleTypes.java":
        "package com.hbm.particle;public class NtmParticleTypes{public static final Ref COOLING_TOWER=new Ref(\"cooling_tower\"),RBMK_FLAME=new Ref(\"rbmkflame\");"
        "public static class Ref{public final String name;Ref(String n){name=n;}public Object get(){return name;}}}",
    "com/hbm/util/particle/ParticleUtil.java":
        "package com.hbm.util.particle;import net.minecraft.world.level.Level;/** Records each added particle (options, position); the production class forwards to Level.addParticle. */"
        "public class ParticleUtil{public record Added(Object options,double x,double y,double z){}public static final java.util.List<Added> ADDED=new java.util.ArrayList<>();"
        "public static void addParticle(Level level,Object options,double x,double y,double z,float xd,float yd,float zd){ADDED.add(new Added(options,x,y,z));}"
        "public static void addParticle(Level level,Object options,double x,double y,double z){ADDED.add(new Added(options,x,y,z));}}",
}


def put_item(items, const, expression):
    """Sets the NtmItems stand-in entry `const` to `new Ref(<expression>)`, adding it when the sources do not name it."""
    match = re.search(r"([\s,])" + const + r"=new Ref\([^)]*\)", items)
    if match:
        return items.replace(match.group(0), match.group(1) + f"{const}=new Ref({expression})", 1)
    if items.count("public static final Ref ") != 1:
        raise SystemExit("Goal 13B: NtmItems does not declare its Refs in one statement")
    return items.replace("public static final Ref ", f"public static final Ref {const}=new Ref({expression}),", 1)


def build_stubs(source, extra_sources=(), vanilla_tags_source="", sources_jar=None):
    """The Goal 13A machine world plus the production arc furnace sources."""
    texts = [(source / name).read_text(encoding="utf-8") for name in GOAL13B_SOURCES]
    stubs = goal13a_stubs(source, list(extra_sources) + texts, vanilla_tags_source, sources_jar)
    if sources_jar is None:
        raise SystemExit("Goal 13B: the NeoForge sources JAR is required for Mth.hsvToRgb")
    # The player's slot model: the menu's slot positions are checked against the original container.
    _replace(stubs, "net/minecraft/world/inventory/Slot.java", "public Slot(Container c,int i,int x,int y){container=c;index=i;}",
             "public final int x,y;public Slot(Container c,int i,int x,int y){container=c;index=i;this.x=x;this.y=y;}")

    # ---- Registry entries -----------------------------------------------------------------------------------------
    items = stubs["com/hbm/items/NtmItems.java"]
    # Built from the production registration (stack size, maximum, burnt item), so a changed constant in NtmItems reaches the fixture.
    for constant, stack, maximum, burnt in electrodes(source):
        items = put_item(items, constant, f"new com.hbm.items.machine.ArcElectrodeItem(new Item.Properties().stacksTo({stack}),{maximum},()->NtmItems.{burnt}.get())")
    for constant in ("NUGGET_SILICON", "BILLET_SILICON"):
        if not re.search(r"[\s,]" + constant + r"=new Ref\(", items):
            items = put_item(items, constant, f'"hbmsntm:{constant.lower()}"')
    stubs["com/hbm/items/NtmItems.java"] = items
    _replace(stubs, "com/hbm/items/component/NtmDataComponents.java", 'COLTAN_Z=new Ref<>("hbmsntm:coltan_z")',
             'COLTAN_Z=new Ref<>("hbmsntm:coltan_z"),ARC_ELECTRODE_DURABILITY=new Ref<>("hbmsntm:arc_electrode_durability")')

    # ---- Minecraft: the bar colour, the translated text with its arguments ---------------------------------------------
    with zipfile.ZipFile(sources_jar) as jar:
        mth = jar.read("net/minecraft/util/Mth.java").decode("utf-8").replace("\r\n", "\n")
    hsv = "\n".join(method_body(mth, signature, "Mth") for signature in (
        "public static int hsvToRgb(float hue, float saturation, float value) {", "public static int hsvToArgb(float hue, float saturation, float value, int alpha) {"))
    _replace(stubs, "net/minecraft/util/Mth.java", "public static int hsvToRgb(float h,float s,float v){return 0;}",
             "// Minecraft 1.21.1 Mth.hsvToRgb and hsvToArgb (NeoForge sources):\n" + hsv + "\n")
    # FastColor.ARGB32.color of Minecraft 1.21.1 (the packing hsvToArgb ends in).
    stubs["net/minecraft/util/FastColor.java"] = ("package net.minecraft.util;public class FastColor{public static class ARGB32{"
                                                  "public static int color(int alpha,int red,int green,int blue){return alpha<<24|red<<16|green<<8|blue;}}}")
    # The machine world's SerializableRecipe stand-in has no readAStack (the table's reader is exercised in the recipe world).
    _replace(stubs, "com/hbm/inventory/recipes/loader/SerializableRecipe.java", "public static AStack[] readAStackArray(JsonArray a){return new AStack[0];}",
             "public static AStack readAStack(JsonArray a){return null;}public static AStack[] readAStackArray(JsonArray a){return new AStack[0];}")
    _replace(stubs, "net/minecraft/network/chat/Component.java", "public static Component translatable(String s,Object... args){return new Component(s);}",
             "public Object[] args=new Object[0];public static Component translatable(String s,Object... args){Component c=new Component(s);c.args=args;return c;}")

    # ---- The client branch of the block entity ---------------------------------------------------------------------------
    _replace(stubs, "com/hbm/util/SoundUtils.java", "public static void playAtVec3(Level l,net.minecraft.world.phys.Vec3 p,Object e,Object s,float v,float pitch){",
             "public static void playAtVec3(Level l,net.minecraft.core.BlockPos.Vec p,Object e,Object s){l.playSound(null,p.x(),p.y(),p.z(),e,s,1F,1F);}\n"
             " public static void playAtVec3(Level l,net.minecraft.world.phys.Vec3 p,Object e,Object s,float v,float pitch){")
    _replace(stubs, "net/minecraft/world/entity/player/Player.java", "public double distanceToSqr(double x,double y,double z){return 0;}",
             "public double px,py,pz;public double distanceToSqr(double x,double y,double z){return (px-x)*(px-x)+(py-y)*(py-y)+(pz-z)*(pz-z);}")
    for name, content in PARTICLE_STUBS.items():
        if name in stubs:
            raise SystemExit(f"Goal 13B: {name} already has a stand-in")
        stubs[name] = content

    # ---- Recipe stacks: the production key semantics of ArcFurnaceRecipes' de-duplication ---------------------------------------
    _replace(stubs, "com/hbm/inventory/RecipesCommon.java", "public ItemStack toStack(){return MetaHelper.newStack(item,stacksize,meta);}",
             "public ItemStack toStack(){return MetaHelper.newStack(item,stacksize,meta);}"
             "public ComparableStack makeSingular(){this.stacksize=1;return this;}"
             "public int hashCode(){return 31*(31*1+item.id.hashCode())+stacksize;}"
             "public boolean equals(Object o){if(this==o)return true;if(o==null||getClass()!=o.getClass())return false;ComparableStack other=(ComparableStack)o;"
             "if(item!=other.item)return false;if(meta!=MetaHelper.WILDCARD_VALUE&&other.meta!=MetaHelper.WILDCARD_VALUE&&meta!=other.meta)return false;return stacksize==other.stacksize;}")
    return stubs


# ---- Recipe world -------------------------------------------------------------------------------------------------------

RECIPES_COMMON = """package com.hbm.inventory;import java.util.*;import net.minecraft.world.item.*;import net.minecraft.world.level.ItemLike;
/** The production AStack, ComparableStack and TagStack semantics the recipe tables call (RecipesCommon.java); a tag stack's members are fixture-set. */
public class RecipesCommon{
 public static final Map<String,List<Item>> TAG_MEMBERS=new HashMap<>();
 public static abstract class AStack{public int stacksize=1;public abstract boolean matchesRecipe(ItemStack stack,boolean ignoreSize);public abstract AStack copy();
  public AStack copy(int size){AStack c=copy();c.stacksize=size;return c;}public abstract List<ItemStack> extractForJEI();public ItemStack extractForCyclingDisplay(int ticks){return ItemStack.EMPTY;}}
 public static class ComparableStack extends AStack{public Item item;public int meta;
  public ComparableStack(ItemStack stack){if(stack.isEmpty()){this.item=new Item("hbmsntm:nothing");this.stacksize=1;return;}this.item=stack.getItem();this.stacksize=stack.getCount();this.meta=MetaHelper.getMeta(stack);}
  public ComparableStack makeSingular(){this.stacksize=1;return this;}
  public ComparableStack(ItemLike item){this.item=item.asItem();this.stacksize=1;this.meta=MetaHelper.WILDCARD_VALUE;}
  public ComparableStack(ItemLike item,int stacksize){this(item);this.stacksize=stacksize;}
  public ComparableStack(ItemLike item,int stacksize,int meta){this(item);this.stacksize=stacksize;this.meta=meta;}
  public ComparableStack(ItemLike item,int stacksize,Enum<?> meta){this(item,stacksize);this.meta=meta.ordinal();}
  public ItemStack toStack(){return MetaHelper.newStack(item,stacksize,meta);}
  public int hashCode(){return 31*(31*1+item.id.hashCode())+stacksize;}
  public boolean equals(Object o){if(this==o)return true;if(o==null||getClass()!=o.getClass())return false;ComparableStack other=(ComparableStack)o;
   if(item!=other.item)return false;if(meta!=MetaHelper.WILDCARD_VALUE&&other.meta!=MetaHelper.WILDCARD_VALUE&&meta!=other.meta)return false;return stacksize==other.stacksize;}
  public ComparableStack copy(){return new ComparableStack(item,stacksize,meta);}
  public boolean matchesRecipe(ItemStack stack,boolean ignoreSize){if(stack==null)return false;if(stack.getItem()!=this.item)return false;
   if(this.meta!=MetaHelper.WILDCARD_VALUE&&MetaHelper.getMeta(stack)!=this.meta)return false;if(!ignoreSize&&stack.getCount()<this.stacksize)return false;return true;}
  public List<ItemStack> extractForJEI(){return Collections.singletonList(this.toStack());}}
 public static class TagStack extends AStack{public net.minecraft.tags.TagKey<Item> tag;
  public TagStack(net.minecraft.tags.TagKey<Item> tag){this.tag=tag;this.stacksize=1;}public TagStack(net.minecraft.tags.TagKey<Item> tag,int stacksize){this(tag);this.stacksize=stacksize;}
  public AStack copy(){return new TagStack(tag,stacksize);}
  public int hashCode(){return 31*(31*1+tag.location().hashCode())+stacksize;}
  public boolean equals(Object o){return o instanceof TagStack t&&t.tag.location().equals(tag.location())&&t.stacksize==stacksize;}
  public boolean matchesRecipe(ItemStack stack,boolean ignoreSize){if(stack.isEmpty())return false;if(!ignoreSize&&stack.getCount()<this.stacksize)return false;
   return stack.getItem().tags.contains(tag.location().toString());}
  public List<ItemStack> extractForJEI(){List<ItemStack> out=new ArrayList<>();for(Item i:TAG_MEMBERS.getOrDefault(tag.location().toString(),List.of()))out.add(new ItemStack(i,this.stacksize));return out;}}}"""


def stamp_item(source):
    """StampItem with the production StampType constants (StampItem.java)."""
    text = (source / STAMP_ITEM).read_text(encoding="utf-8")
    match = re.search(r"enum StampType\s*\{([^}]*)\}", text)
    if match is None:
        raise SystemExit("Goal 13B: no StampType in StampItem")
    constants = ",".join(name.strip() for name in match.group(1).split(",") if name.strip())
    return ("package com.hbm.items.machine;/** The production StampType constants; the item carries its type. */public class StampItem extends net.minecraft.world.item.Item{"
            f"public enum StampType{{{constants}}}public final StampType type;public StampItem(String id,StampType t){{super(id);type=t;}}}}")


def recipe_stubs(source, extra_texts=()):
    """The Goal 13A recipe world with the production ArcFurnaceRecipes and PressRecipes compiled."""
    stubs = goal13a_recipe_stubs(source, extra_texts)
    for name in GOAL13B_RECIPE_SOURCES:
        if stubs.pop(name, None) is None:
            raise SystemExit(f"Goal 13B: the Goal 3C name-only stand-in {name} was not found")
    texts = [(source / name).read_text(encoding="utf-8") for name in GOAL13B_RECIPE_SOURCES] + list(extra_texts)

    stubs["com/hbm/inventory/RecipesCommon.java"] = RECIPES_COMMON
    stubs[STAMP_ITEM] = stamp_item(source)
    _declare(stubs, "net/minecraft/world/item/Items.java", "public class Items{", "Item",
             names(r"(?<![A-Za-z_.])Items\.([A-Z][A-Z_0-9]*)\b", *texts), lambda n: f'new Item("minecraft:{n.lower()}")')
    _declare(stubs, "net/minecraft/world/level/block/Blocks.java", "public class Blocks{", "Item",
             names(r"(?<![A-Za-z_.])Blocks\.([A-Z][A-Z_0-9]*)\b", *texts), lambda n: f'new Item("minecraft:{n.lower()}")')
    _declare(stubs, "com/hbm/items/NtmItems.java", "public class NtmItems{", "Ref", names(r"NtmItems\.([A-Z][A-Z_0-9]*)\b", *texts), lambda n: f'new Ref("{n}")')
    _declare(stubs, "com/hbm/blocks/NtmBlocks.java", "public class NtmBlocks{", "Ref", names(r"NtmBlocks\.([A-Z][A-Z_0-9]*)\b", *texts), lambda n: f'new Ref("{n}")')
    return stubs
