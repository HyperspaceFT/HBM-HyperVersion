"""Goal 11C stand-ins: three worlds for the chemical plant, its recipes and the shredder entry.

* the recipe world (recipe_stubs): the Goal 11B recipe world (the Goal 11A/3C loader world with real Gson and the production
  SerializableRecipe, GenericRecipes, GenericRecipe) extended so the production ChemicalPlantRecipes compiles next to
  AssemblyMachineRecipes: every fluid the sources name is a FluidType with its own name and id (getUnlocalizedName is
  "hbmfluid." + the lower-case name, as the production FluidType; the writer wrote it until Goal 11D and writes
  getInternalName, the name itself, since), vanilla Items and Blocks are
  generated from the names the sources use ("minecraft:" ids), MetaHelper keeps the meta of a stack (as the Goal 3C
  processing world does), ItemTags.SAND, ResourceLocation.withDefaultNamespace, a one-argument TagStack and the item enums
  the chemical plant recipes name (stand-in constants; their meta is the stand-in ordinal, the same for the live table and
  its post-Goal 11B copy, and no exported reference contains one);
* the shredder world (shredder_stubs): the Goal 4 shredder recipe world (production SerializableRecipe, GenericRecipes,
  GenericRecipe, ShredderRecipes, real Gson, a scratch config directory) unchanged, with the item and block references of
  the post-Goal 11B ShredderRecipes copy;
* the machine world (build_stubs): the Goal 11B machine world (goal11b_regression/stubs.py: the Goal 10C networks, the
  combination oven, AnvilRecipes, the Goal 11A derrick and the Goal 11B refinery and tank) extended with what the
  production chemical plant (block entity, module, menu with the production SlotCraftingOutput, ChemicalPlantRecipes) and
  the production BlueprintsItem need; see
  goal11c_regression/README.md.
"""

import re
import zipfile

from goal10b_regression.stubs import method_body
from goal11b_regression.stubs import build_stubs as goal11b_stubs, recipe_stubs as goal11b_recipe_stubs

ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"
CHEM_RECIPES = "com/hbm/inventory/recipes/ChemicalPlantRecipes.java"
SHREDDER = "com/hbm/inventory/recipes/ShredderRecipes.java"
CHEM_BE = "com/hbm/blockentity/machine/MachineChemicalPlantBlockEntity.java"
CHEM_MODULE = "com/hbm/module/machine/ModuleMachineChemicalPlant.java"
MODULE_BASE = "com/hbm/module/machine/ModuleMachineBase.java"
CHEM_MENU = "com/hbm/inventory/menus/MachineChemicalPlantMenu.java"
BLUEPRINTS = "com/hbm/items/machine/BlueprintsItem.java"
GENERIC_RECIPE = "com/hbm/inventory/recipes/loader/GenericRecipe.java"
ANVIL_SMITHING = "com/hbm/inventory/recipes/anvil/AnvilSmithingRecipe.java"
SLOT_OUTPUT = "com/hbm/inventory/SlotCraftingOutput.java"
# Production sources the machine world compiles on top of the Goal 11B machine world.
GOAL11C_SOURCES = (MODULE_BASE, CHEM_MODULE, CHEM_BE, CHEM_MENU, CHEM_RECIPES, BLUEPRINTS, ANVIL_SMITHING, SLOT_OUTPUT)


def _require(text, old, label):
    if old not in text:
        raise SystemExit(f"Goal 11C stub anchor missing in {label}: {old[:70]}")
    return text


def _replace(stubs, name, old, new):
    stubs[name] = _require(stubs[name], old, name).replace(old, new)


def names(pattern, *texts):
    """The distinct names a regex finds in the texts, in order of first appearance."""
    return list(dict.fromkeys(m for text in texts for m in re.findall(pattern, text)))


# ---- Recipe world -------------------------------------------------------------------------------------------------------

def recipe_stubs(source, base_assembly, base_chem):
    """The Goal 11B recipe world for the live AssemblyMachineRecipes and ChemicalPlantRecipes and their post-Goal 11B copies
    (package goal11c.base)."""
    live_assembly = (source / ASSEMBLY).read_text(encoding="utf-8")
    live_chem = (source / CHEM_RECIPES).read_text(encoding="utf-8")
    texts = (live_assembly, base_assembly, live_chem, base_chem)
    # The Goal 11B world reads the live assembly table itself; the other texts only feed its NtmItems/NtmBlocks names.
    stubs = goal11b_recipe_stubs(source, "\n".join(texts[1:]))
    stubs.pop(CHEM_RECIPES)

    fluids = ["NONE"] + [f for f in names(r"Fluids\.([A-Z][A-Z_0-9]*)\b", *texts) if f != "NONE"]
    stubs["com/hbm/inventory/fluid/Fluids.java"] = (
        "package com.hbm.inventory.fluid;public class Fluids{public static final FluidType "
        + ",".join(f'{f}=new FluidType("{f}",{i})' for i, f in enumerate(fluids))
        + ";public static FluidType fromName(String s){for(FluidType t:getInNiceOrder())if(t.getInternalName().equals(s))return t;return NONE;}"
        "public static FluidType[] getInNiceOrder(){return new FluidType[]{" + ",".join(fluids) + "};}}")
    stubs["com/hbm/inventory/fluid/FluidType.java"] = (
        "package com.hbm.inventory.fluid;import net.minecraft.network.chat.*;"
        "/** Named like the production FluidType: getUnlocalizedName() is \"hbmfluid.\" + the lower-case name (FluidType.java:61). */"
        "public class FluidType{private final String name;private final int id;public FluidType(){this(\"NONE\",0);}public FluidType(String n,int i){name=n;id=i;}"
        "public String getInternalName(){return name;}public String getUnlocalizedName(){return \"hbmfluid.\"+name.toLowerCase(java.util.Locale.US);}"
        "public int getID(){return id;}public boolean hasNoContainer(){return true;}public MutableComponent getName(){return Component.literal(name);}"
        "public <T> T getTrait(Class<T> c){return null;}public String toString(){return name;}}")

    vanilla_items = ["OAK_LOG", "OAK_WOOD", "OAK_PLANKS", "OAK_SAPLING", "CHARCOAL", "COAL", "STONE"]
    vanilla_items += [n for n in names(r"(?<![A-Za-z_.])Items\.([A-Z][A-Z_0-9]*)\b", *texts) if n not in vanilla_items]
    stubs["net/minecraft/world/item/Items.java"] = (
        "package net.minecraft.world.item;public class Items{public static final Item "
        + ",".join(f'{n}=new Item("minecraft:{n.lower()}")' for n in vanilla_items) + ";}")
    vanilla_blocks = names(r"(?<![A-Za-z_.])Blocks\.([A-Z][A-Z_0-9]*)\b", *texts)
    # The recipe world has no Block class; a block is used here only as an ingredient or output, so its item stands in.
    stubs["net/minecraft/world/level/block/Blocks.java"] = (
        "package net.minecraft.world.level.block;import net.minecraft.world.item.Item;public class Blocks{public static final Item "
        + ",".join(f'{n}=new Item("minecraft:{n.lower()}")' for n in vanilla_blocks) + ";}")
    stubs["net/minecraft/tags/ItemTags.java"] = (
        "package net.minecraft.tags;import net.minecraft.resources.*;import net.minecraft.world.item.*;public class ItemTags{"
        "public static final TagKey<Item> SAND=create(ResourceLocation.withDefaultNamespace(\"sand\"));"
        "public static TagKey<Item> create(ResourceLocation id){return new TagKey<>(id);}}")
    _replace(stubs, "net/minecraft/resources/ResourceLocation.java", " public String toString(){",
             " public static ResourceLocation withDefaultNamespace(String p){return new ResourceLocation(\"minecraft\",p);}\n public String toString(){")
    _replace(stubs, "com/hbm/inventory/RecipesCommon.java", "public TagStack(net.minecraft.tags.TagKey<Item> tag,int n){super(n);this.tag=tag;}",
             "public TagStack(net.minecraft.tags.TagKey<Item> tag,int n){super(n);this.tag=tag;}public TagStack(net.minecraft.tags.TagKey<Item> tag){this(tag,1);}")
    # As the Goal 3C processing world: the meta travels with the stack, so an output's meta reaches the writer.
    stubs["com/hbm/inventory/MetaHelper.java"] = (
        "package com.hbm.inventory;import net.minecraft.world.item.*;import net.minecraft.world.level.ItemLike;public class MetaHelper{"
        "public static final int WILDCARD_VALUE=32767;public static int getMeta(ItemStack s){try{return Integer.parseInt(s.component());}catch(Exception e){return 0;}}"
        "public static ItemStack newStack(ItemLike i,int n,int m){return new ItemStack(i,n).component(Integer.toString(m));}}")

    def enum(package, cls, constants, meta=False, nested="Type"):
        body = ",".join(constants) + ";" + ("public final int meta=ordinal();" if meta else "")
        return f"package {package};public class {cls}{{public enum {nested}{{{body}}}}}"

    stubs["com/hbm/items/FuelAdditiveItem.java"] = enum("com.hbm.items", "FuelAdditiveItem", names(r"FuelAdditiveItem\.Type\.([A-Z_0-9]+)", *texts))
    stubs["com/hbm/items/BoltItem.java"] = enum("com.hbm.items", "BoltItem", names(r"BoltItem\.Type\.([A-Z_0-9]+)", *texts), meta=True)
    stubs["com/hbm/items/WireDenseItem.java"] = enum("com.hbm.items", "WireDenseItem", names(r"WireDenseItem\.Type\.([A-Z_0-9]+)", *texts), meta=True)
    stubs["com/hbm/items/RawIngotItem.java"] = "package com.hbm.items;public class RawIngotItem{}"
    part = ["STEEL"] + [n for n in names(r"PartGenericItem\.Type\.([A-Z_0-9]+)", *texts) if n != "STEEL"]
    stubs["com/hbm/items/PartGenericItem.java"] = enum("com.hbm.items", "PartGenericItem", part)
    packs = ["BASIC"] + [n for n in names(r"BatteryPackType\.([A-Z_0-9]+)", *texts) if n != "BASIC"]
    stubs["com/hbm/items/machine/BatteryPackItem.java"] = enum("com.hbm.items.machine", "BatteryPackItem", packs, nested="BatteryPackType")
    return stubs


# ---- Machine world ------------------------------------------------------------------------------------------------------

def _declare(stubs, name, opening, kind, constants, make):
    """Adds `public static final <kind> NAME=<make(NAME)>` for every constant the stand-in class does not declare yet."""
    text = stubs[name]
    missing = [c for c in constants if not re.search(r"[\s,]" + c + r"=", text)]
    if missing:
        _replace(stubs, name, opening, opening + f"public static final {kind} " + ",".join(f"{c}={make(c)}" for c in missing) + ";")
    return missing


def generic_recipe(source):
    """GenericRecipe with the production pool, setup and builder bodies (GenericRecipe.java); the 528 config check of
    setPools and the stack-limit check of inputItems are left out (no config, no oversized stack in the table)."""
    text = (source / GENERIC_RECIPE).read_text(encoding="utf-8").replace("\r\n", "\n")
    bodies = [method_body(text, signature, "GenericRecipe") for signature in (
        "public boolean isPooled() {", "public String[] getPools() {", "public boolean isPartOfPool(String lookingFor) {",
        "public GenericRecipe setDuration(int duration) {", "public GenericRecipe setPower(long power) {",
        "public GenericRecipe setup(int duration, long power) {", "public GenericRecipe setupNamed(int duration, long power) {",
        "public GenericRecipe setNameWrapper(String wrapper) {", "public GenericRecipe setIcon(ItemStack icon) {",
        "public GenericRecipe setIcon(ItemLike item, int meta) {", "public GenericRecipe setIcon(ItemLike item) {",
        "public GenericRecipe setNamed() {", "public GenericRecipe inputFluids(FluidStack... input) {",
        "public GenericRecipe outputItems(IOutput... output) {", "public GenericRecipe outputFluids(FluidStack... output) {",
        "public String getInternalName() {")]
    return ("package com.hbm.inventory.recipes.loader;import com.hbm.inventory.*;import com.hbm.inventory.RecipesCommon.AStack;"
            "import com.hbm.inventory.recipes.loader.GenericRecipes.IOutput;import net.minecraft.world.item.*;import net.minecraft.world.level.ItemLike;\n"
            "public class GenericRecipe{protected final String name;public String nameWrapper;public AStack[] inputItem;public FluidStack[] inputFluid;"
            "public IOutput[] outputItem;public FluidStack[] outputFluid;public int duration;public long power;protected ItemStack icon;"
            "public boolean writeIcon=false;public boolean customLocalization=false;protected String[] blueprintPools=null;public String autoSwitchGroup=null;\n"
            "public GenericRecipe(String name){this.name=name;}\n"
            # Production GenericRecipe.getName() for a named recipe (Goal 13A); an unnamed recipe's icon display name is not modelled and answers a literal.
            "public net.minecraft.network.chat.Component getName(){return customLocalization?net.minecraft.network.chat.Component.translatable(this.name)"
            ":net.minecraft.network.chat.Component.literal(\"icon:\"+this.name);}\n"
            "// Production GenericRecipe.java bodies:\n" + "\n".join(bodies) + "\n"
            "public GenericRecipe setPools(String... pools){this.blueprintPools=pools;for(String pool:pools)GenericRecipes.addToPool(pool,this);return this;}\n"
            "public GenericRecipe inputItems(AStack... input){this.inputItem=input;return this;}\n"
            # A single output with chance 1 and weight 0, as the production ChanceOutput from outputItems(ItemStack...).
            "public GenericRecipe outputItems(ItemStack... stacks){outputItem=new IOutput[stacks.length];for(int i=0;i<stacks.length;i++)outputItem[i]=new Single(stacks[i]);return this;}\n"
            "public static class Single implements IOutput{private final ItemStack stack;public Single(ItemStack s){stack=s;}public boolean possibleMultiOutput(){return false;}"
            "public ItemStack getSingle(){return stack.copy();}public ItemStack collapse(){return stack.copy();}public java.util.List<ItemStack> getAllPossibilities(){return java.util.List.of(stack);}}}")


GENERIC_RECIPES = """package com.hbm.inventory.recipes.loader;import java.util.*;
/** The Goal 11B stand-in plus the production static pool registry (GenericRecipes.java blueprintPools, addToPool, addToGroup). */
public abstract class GenericRecipes<T extends GenericRecipe> {public final Map<String,T> recipeNameMap=new HashMap<>();public final List<T> recipeOrderedList=new ArrayList<>();public final Map<String,List<GenericRecipe>> autoSwitchGroups=new HashMap<>();
 public static final String POOL_PREFIX_ALT="alt.",POOL_PREFIX_DISCOVER="discover.",POOL_PREFIX_SECRET="secret.",POOL_PREFIX_528="528.";
 public static HashMap<String,List<String>> blueprintPools=new HashMap<>();
 // Production GenericRecipes.java:48-67 and :77-80 (the pool registry the blueprint hover text reads; Goal 13A):
 public static HashMap<String,GenericRecipe> pooledBlueprints=new HashMap<>();
 public static void addToPool(String pool,GenericRecipe recipe){List<String> list=blueprintPools.computeIfAbsent(pool,k->new ArrayList<>());list.add(recipe.getInternalName());pooledBlueprints.put(recipe.getInternalName(),recipe);}
 public static void clearPools(){blueprintPools.clear();pooledBlueprints.clear();}
 public void addToGroup(String group,GenericRecipe recipe){autoSwitchGroups.computeIfAbsent(group,k->new ArrayList<>()).add(recipe);}
 public interface IOutput{boolean possibleMultiOutput();net.minecraft.world.item.ItemStack getSingle();net.minecraft.world.item.ItemStack collapse();java.util.List<net.minecraft.world.item.ItemStack> getAllPossibilities();}
 public void register(T recipe){if(recipeNameMap.putIfAbsent(recipe.getInternalName(),recipe)!=null)throw new IllegalStateException("duplicate "+recipe.getInternalName());recipeOrderedList.add(recipe);}
 public void deleteRecipes(){recipeNameMap.clear();recipeOrderedList.clear();autoSwitchGroups.clear();}
 public abstract int inputItemLimit();public abstract int inputFluidLimit();public abstract int outputItemLimit();public abstract int outputFluidLimit();public abstract String getFileName();public abstract T instantiateRecipe(String n);
 public void registerDefaults(){} }"""


def vanilla_move(sources_jar):
    """Minecraft 1.21.1's AbstractContainerMenu.moveItemStackTo, read from the NeoForge sources JAR (AbstractContainerMenu.java:630)."""
    with zipfile.ZipFile(sources_jar) as jar:
        text = jar.read("net/minecraft/world/inventory/AbstractContainerMenu.java").decode("utf-8").replace("\r\n", "\n")
    return method_body(text, "protected boolean moveItemStackTo(ItemStack stack, int startIndex, int endIndex, boolean reverseDirection) {",
                       "AbstractContainerMenu")


def anvil_variants(source):
    """The production NTMAnvilBlock tier constants and Variant constants with their tier, in declaration order."""
    text = (source / "com/hbm/blocks/machine/NTMAnvilBlock.java").read_text(encoding="utf-8")
    tiers = dict(re.findall(r"public static final int (TIER_[A-Z_]+) = (\d+);", text))
    body = re.search(r"public enum Variant \{(.*?);", text, re.S).group(1)
    variants = re.findall(r"^\s*([A-Z_]+)\((TIER_[A-Z_]+),", body, re.M)
    if not tiers or not variants:
        raise SystemExit("Goal 11C: NTMAnvilBlock tiers or variants not found")
    return tiers, variants


def build_stubs(source, extra_sources=(), vanilla_tags_source="", sources_jar=None):
    """The Goal 11B machine world plus the chemical plant, its module, menu and recipe table, the production
    BlueprintsItem and AnvilSmithingRecipe."""
    texts = [(source / name).read_text(encoding="utf-8") for name in GOAL11C_SOURCES]
    stubs = goal11b_stubs(source, list(extra_sources) + texts, vanilla_tags_source)
    # Compiled from production here.
    for name in (BLUEPRINTS, ANVIL_SMITHING, SLOT_OUTPUT):
        stubs.pop(name)
    all_texts = "\n".join(texts)
    # The special smithing entries (cyanide, rename, cast mold) stay stand-ins on the production base class; they match
    # nothing here (the chain only looks for the desh anvil upgrade). The two Goal 17A mold entries (ingot, blade) are the same kind
    # of stand-in; AnvilRecipes registers them (Goal 19A harness revival).
    for special in ("AnvilSmithingCyanideRecipe", "AnvilSmithingRenameRecipe", "AnvilSmithingCastMoldRecipe",
                    "AnvilSmithingIngotMoldRecipe", "AnvilSmithingBladeMoldRecipe"):
        stubs[f"com/hbm/inventory/recipes/anvil/{special}.java"] = (
            f"package com.hbm.inventory.recipes.anvil;import net.minecraft.world.item.ItemStack;public class {special} extends AnvilSmithingRecipe{{"
            f"public {special}(){{super(1,ItemStack.EMPTY,null,null);}}public int matchesInt(ItemStack l,ItemStack r){{return -1;}}}}")
    _replace(stubs, "com/hbm/util/BobMathUtil.java", "public class BobMathUtil{",
             "public class BobMathUtil{public static long max(long... n){long m=Long.MIN_VALUE;for(long x:n)m=Math.max(m,x);return m;}")

    # ---- Registry entries -----------------------------------------------------------------------------------------
    _replace(stubs, "com/hbm/blockentity/NtmBlockEntityTypes.java", "BATTERY_SOCKET=new Ref()", "BATTERY_SOCKET=new Ref(),MACHINE_CHEMICAL_PLANT=new Ref()")
    _replace(stubs, "com/hbm/inventory/NtmMenuTypes.java", "BATTERY_SOCKET=new Ref()", "BATTERY_SOCKET=new Ref(),MACHINE_CHEMICAL_PLANT=new Ref()")
    _replace(stubs, "com/hbm/registry/NtmSoundEvents.java", "BOILER=new Ref()", "BOILER=new Ref(),CHEMICAL_PLANT_OPERATE=new Ref()")
    # Goal 13A: BlueprintsItem.use reads Player.getAbilities().instabuild and answers InteractionResultHolder.consume/success.
    stubs["net/minecraft/world/entity/player/Abilities.java"] = (
        "package net.minecraft.world.entity.player;/** Only instabuild (creative mode) is modelled. */public class Abilities{public boolean instabuild;}")
    _replace(stubs, "net/minecraft/world/entity/player/Player.java", "public net.minecraft.util.RandomSource getRandom(){return random;}",
             "public net.minecraft.util.RandomSource getRandom(){return random;}"
             "private final Abilities abilities=new Abilities();public Abilities getAbilities(){abilities.instabuild=creative;return abilities;}")
    stubs["net/minecraft/world/InteractionResultHolder.java"] = (
        "package net.minecraft.world;/** Only the result and the value are modelled (the sided result of 1.21.1). */public class InteractionResultHolder<T>{"
        "public enum Kind{SUCCESS,CONSUME,PASS,FAIL}public final Kind kind;public final T value;private InteractionResultHolder(Kind k,T v){kind=k;value=v;}"
        "public static <T> InteractionResultHolder<T> pass(T v){return new InteractionResultHolder<>(Kind.PASS,v);}"
        "public static <T> InteractionResultHolder<T> consume(T v){return new InteractionResultHolder<>(Kind.CONSUME,v);}"
        "public static <T> InteractionResultHolder<T> success(T v){return new InteractionResultHolder<>(Kind.SUCCESS,v);}"
        "public static <T> InteractionResultHolder<T> fail(T v){return new InteractionResultHolder<>(Kind.FAIL,v);}}")
    # The blueprint registry item is a production BlueprintsItem (grabPool compares with NtmItems.BLUEPRINTS.get(), the
    # menu routes by instanceof BlueprintsItem).
    items = stubs["com/hbm/items/NtmItems.java"]
    match = re.search(r"([\s,])BLUEPRINTS=new Ref\([^)]*\)", items)
    if match:
        items = items.replace(match.group(0), match.group(1) + "BLUEPRINTS=new Ref(new com.hbm.items.machine.BlueprintsItem(new Item.Properties()))")
    else:
        items = items.replace("public static final Ref ", "public static final Ref BLUEPRINTS=new Ref(new com.hbm.items.machine.BlueprintsItem(new Item.Properties())),", 1)
    stubs["com/hbm/items/NtmItems.java"] = items
    stubs["com/hbm/items/IMetaItem.java"] = ("package com.hbm.items;import net.minecraft.world.item.*;import java.util.List;"
                                            "public interface IMetaItem{void getSubItems(Item item,List<ItemStack> stacks);}")

    # ---- Recipes ----------------------------------------------------------------------------------------------------
    stubs[GENERIC_RECIPE] = generic_recipe(source)
    stubs["com/hbm/inventory/recipes/loader/GenericRecipes.java"] = GENERIC_RECIPES
    fluids = stubs["com/hbm/inventory/fluid/Fluids.java"]
    ids = [int(n) for n in re.findall(r"=new FluidType\((\d+),", fluids)]
    wanted = names(r"Fluids\.([A-Z][A-Z_0-9]*)\b", all_texts)
    missing = [f for f in wanted if not re.search(r"[\s,]" + f + r"=new FluidType", fluids)]
    if missing:
        start = max(ids) + 1
        decl = "public static final FluidType " + ",".join(f"{f}=new FluidType({start + i},false,false)" for i, f in enumerate(missing)) + ";"
        fluids = fluids.replace("public static final FluidType NONE=", decl + "public static final FluidType NONE=", 1)
        get_all = re.search(r"public static FluidType\[\] getAll\(\)\{return new FluidType\[\]\{([^}]*)\};\}", fluids)
        fluids = fluids.replace(get_all.group(0), get_all.group(0).replace(get_all.group(1), get_all.group(1) + "," + ",".join(missing)))
        stubs["com/hbm/inventory/fluid/Fluids.java"] = fluids
    _declare(stubs, "net/minecraft/world/item/Items.java", "public class Items{", "Item",
             names(r"(?<![A-Za-z_.])Items\.([A-Z][A-Z_0-9]*)\b", all_texts), lambda n: f'new Item("minecraft:{n.lower()}")')
    _declare(stubs, "net/minecraft/world/level/block/Blocks.java", "public class Blocks{", "Block",
             names(r"(?<![A-Za-z_.])Blocks\.([A-Z][A-Z_0-9]*)\b", all_texts), lambda n: f'new Block("minecraft:{n.lower()}")')
    _replace(stubs, "net/minecraft/tags/ItemTags.java", "public class ItemTags{", "public class ItemTags{public static final String SAND=\"minecraft:sand\";")
    _replace(stubs, "net/minecraft/resources/ResourceLocation.java", " public String getPath(){",
             " public static ResourceLocation withDefaultNamespace(String p){return new ResourceLocation(\"minecraft\",p);}\n public String getPath(){")
    stubs["com/hbm/items/FuelAdditiveItem.java"] = ("package com.hbm.items;public class FuelAdditiveItem{public enum Type{"
                                                   + ",".join(names(r"FuelAdditiveItem\.Type\.([A-Z_0-9]+)", all_texts)) + "}}")
    stubs["com/hbm/items/RawIngotItem.java"] = "package com.hbm.items;public class RawIngotItem{}"
    tiers, variants = anvil_variants(source)
    stubs["com/hbm/blocks/machine/NTMAnvilBlock.java"] = (
        "package com.hbm.blocks.machine;/** The production tier constants and Variant tiers (NTMAnvilBlock.java). */public class NTMAnvilBlock{"
        + "".join(f"public static final int {k}={v};" for k, v in tiers.items())
        + "public enum Variant{" + ",".join(f"{n}({t})" for n, t in variants) + ";public final int tier;Variant(int t){tier=t;}}}")

    # ---- Menus: Minecraft's quick-move merge ----------------------------------------------------------------------------
    if sources_jar is not None:
        menu = stubs["net/minecraft/world/inventory/AbstractContainerMenu.java"]
        start = menu.index(" protected boolean moveItemStackTo(")
        end = menu.index("return changed;}", start) + len("return changed;}")
        stubs["net/minecraft/world/inventory/AbstractContainerMenu.java"] = (
            menu[:start] + "\n// Minecraft 1.21.1 AbstractContainerMenu.moveItemStackTo (NeoForge sources):\n" + vanilla_move(sources_jar) + "\n" + menu[end:])
        _replace(stubs, "net/minecraft/world/inventory/Slot.java", "public int getMaxStackSize(){return container.getMaxStackSize();}",
                 "public int getMaxStackSize(){return container.getMaxStackSize();}"
                 "public int getMaxStackSize(ItemStack s){return Math.min(this.getMaxStackSize(),s.getMaxStackSize());}"
                 "public boolean mayPickup(net.minecraft.world.entity.player.Player p){return true;}")
        _replace(stubs, "net/minecraft/world/item/ItemStack.java", "public ItemStack copyWithCount(int n){",
                 "public boolean isStackable(){return getMaxStackSize()>1&&(!isDamageableItem()||getDamageValue()==0);}"
                 "public ItemStack split(int n){int i=Math.min(n,getCount());ItemStack s=copyWithCount(i);shrink(i);return s;}"
                 "public ItemStack copyWithCount(int n){")
    return stubs


# ---- Shredder world -----------------------------------------------------------------------------------------------------

def shredder_stubs(source, base_shredder, fixture_text=""):
    """The Goal 4 shredder recipe world, with the item and block names of the live ShredderRecipes, its post-Goal 11B
    copy and the fixture (so a mutation that removes the only reference to an item still compiles)."""
    from goal4_recipe_regression.stubs import make_stubs as goal4_stubs

    live = (source / SHREDDER).read_text(encoding="utf-8")
    return goal4_stubs(live + "\n" + base_shredder + "\n" + fixture_text)
