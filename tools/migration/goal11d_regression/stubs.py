"""Goal 11D stand-ins: the recipe world of the fluid name in the recipe template export.

recipe_stubs() is the Goal 11C recipe world (goal11c_regression/stubs.py recipe_stubs: the Goal 11B/11A/3C loader world
with real Gson and the production SerializableRecipe, GenericRecipes and GenericRecipe; every fluid the sources name is a
FluidType whose getInternalName() is the Fluids field name and whose getUnlocalizedName() is "hbmfluid." + the lower-case
name, as the production FluidType.java:61 and :157-159) extended so that the production SolderingRecipes and
ArcWelderRecipes compile next to AssemblyMachineRecipes and ChemicalPlantRecipes:

* the Goal 3C name-only handler stand-ins of the two tables are dropped (the production classes are compiled);
* DeferredItem<T> is a stand-in base class of the NtmItems registry references (SolderingRecipes takes DeferredItem<Item>,
  as the production NtmItems fields are);
* AStack.matchesRecipe(ItemStack, boolean) exists (used by the tables' matchers, not exercised here);
* MetaHelper.newStack(ItemLike, [int,] Enum) keeps the enum ordinal as the meta, as the production MetaHelper.java:37-41.

The Goal 11C world's base-copy slots only feed the names the stand-ins declare; Goal 11D changes no table, so the
soldering and arc welder texts fill them. No production source is replaced by a stand-in (verify_goal11d.py refuses to run
otherwise). Item metas of stand-in enums (PartGenericItem, BoltItem, ...) are stand-in ordinals; they are identical in the
production and the post-Goal 11C world and are not compared with the game.
"""

from goal11c_regression.stubs import _replace, recipe_stubs as goal11c_recipe_stubs

ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"
CHEM_RECIPES = "com/hbm/inventory/recipes/ChemicalPlantRecipes.java"
SOLDERING = "com/hbm/inventory/recipes/SolderingRecipes.java"
ARC_WELDER = "com/hbm/inventory/recipes/ArcWelderRecipes.java"
SERIALIZABLE = "com/hbm/inventory/recipes/loader/SerializableRecipe.java"
GENERIC_RECIPES = "com/hbm/inventory/recipes/loader/GenericRecipes.java"
GENERIC_RECIPE = "com/hbm/inventory/recipes/loader/GenericRecipe.java"
TABLES = (CHEM_RECIPES, ASSEMBLY, SOLDERING, ARC_WELDER)


def recipe_stubs(source):
    """The Goal 11C recipe world for the four production tables that call SerializableRecipe.writeFluidStack."""
    soldering = (source / SOLDERING).read_text(encoding="utf-8")
    arc = (source / ARC_WELDER).read_text(encoding="utf-8")
    stubs = goal11c_recipe_stubs(source, soldering, arc)
    for name in (SOLDERING, ARC_WELDER):
        if name not in stubs:
            raise SystemExit(f"Goal 11D: the Goal 3C handler stand-in {name} was not found")
        stubs.pop(name)

    stubs["net/neoforged/neoforge/registries/DeferredItem.java"] = (
        "package net.neoforged.neoforge.registries;import net.minecraft.world.item.Item;import net.minecraft.world.level.ItemLike;"
        "public abstract class DeferredItem<T extends Item> implements ItemLike{public abstract T get();}")
    _replace(stubs, "com/hbm/items/NtmItems.java", "public static class Ref implements ItemLike{",
             "public static class Ref extends net.neoforged.neoforge.registries.DeferredItem<Item> implements ItemLike{")
    _replace(stubs, "com/hbm/inventory/RecipesCommon.java", "public static class AStack{public int stacksize;public AStack(int n){stacksize=n;}",
             "public static class AStack{public int stacksize;public AStack(int n){stacksize=n;}"
             "public boolean matchesRecipe(ItemStack s,boolean ignoreSize){return false;}")
    # Production MetaHelper.java:37-41: an enum stands for its ordinal.
    _replace(stubs, "com/hbm/inventory/MetaHelper.java", "public static ItemStack newStack(ItemLike i,int n,int m){",
             "public static ItemStack newStack(ItemLike i,Enum<?> e){return newStack(i,1,e.ordinal());}"
             "public static ItemStack newStack(ItemLike i,int n,Enum<?> e){return newStack(i,n,e.ordinal());}"
             "public static ItemStack newStack(ItemLike i,int n,int m){")
    return stubs
