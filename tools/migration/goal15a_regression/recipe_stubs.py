"""Reuse 14C loader services; the new assembly table is compiled unchanged."""
from goal14c_regression.recipe_stubs import recipe_stubs as base_stubs, RECIPE_SOURCES
from goal10b_regression.stubs import ordinal_enum, meta_enum, method_body

def recipe_stubs(source, extras):
    stubs = base_stubs(source, extras)
    p = 'com/hbm/items/machine/PistonSetItem.java'
    stubs[p] = ordinal_enum((source/p).read_text(encoding='utf-8'),'com.hbm.items.machine','PistonSetItem','production PistonSetItem')
    p = 'com/hbm/items/BoltItem.java'
    stubs[p] = meta_enum((source/p).read_text(encoding='utf-8'),'com.hbm.items','BoltItem','production BoltItem')
    p = 'com/hbm/items/WireDenseItem.java'
    stubs[p] = meta_enum((source/p).read_text(encoding='utf-8'),'com.hbm.items','WireDenseItem','production WireDenseItem')
    p = 'com/hbm/inventory/RecipesCommon.java'
    production = (source/p).read_text(encoding='utf-8')
    production = production[production.index('public static class ComparableStack'):production.index('public static class TagStack')]
    service = stubs[p]
    section = service[service.index('public static class ComparableStack'):service.index('public static class TagStack')]
    before = method_body(section,'public boolean matchesRecipe(ItemStack stack,boolean ignoreSize){','inherited ComparableStack service')
    after = method_body(production,'public boolean matchesRecipe(ItemStack stack, boolean ignoreSize) {','production ComparableStack')
    assert service.count(before)==1
    stubs[p] = service.replace(before,after,1)
    return stubs
