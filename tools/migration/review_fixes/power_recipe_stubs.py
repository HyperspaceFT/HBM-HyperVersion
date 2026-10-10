"""Reuse the mature network and real-Gson worlds without editing their shared fixtures."""
from goal10b_regression.stubs import build_machine_stubs
from goal11d_regression.stubs import recipe_stubs


def machine_stubs(source):
    return build_machine_stubs(source)


def custom_recipe_stubs(source):
    stubs = recipe_stubs(source)
    name = "com/hbm/inventory/RecipesCommon.java"
    old = "public boolean matchesRecipe(ItemStack s,boolean ignoreSize){return false;}"
    # The recipe loader world's old comparator was deliberately inert. Enable exact item matching for
    # this fixture's meta-0 custom recipes; Minecraft tags/components remain outside this world.
    new = ("public boolean matchesRecipe(ItemStack s,boolean ignoreSize){return this instanceof ComparableStack c"
           " && !s.isEmpty() && c.item==s.getItem() && (ignoreSize || s.getCount()>=stacksize);}")
    if stubs[name].count(old) != 1:
        raise AssertionError("recipe comparator fixture anchor changed")
    stubs[name] = stubs[name].replace(old, new)
    return stubs
