"""Goal 16A acquisition test services built from the existing Goal 10A world."""

from goal10a_regression.stubs import build_machine_stubs


def build_stubs(source):
    stubs = build_machine_stubs(source)

    items = stubs["com/hbm/items/NtmItems.java"]
    anchor = 'INGOT_DURA_STEEL=new Ref(new Item("hbmsntm:ingot_dura_steel"))'
    if anchor not in items:
        raise SystemExit("Goal 16A stub anchor missing: Dura ingot item")
    stubs["com/hbm/items/NtmItems.java"] = items.replace(
        anchor, anchor + ',MOLD_INGOT=new Ref(new Item("hbmsntm:mold_ingot"))', 1
    )

    stubs["net/minecraft/world/item/Items.java"] = (
        'package net.minecraft.world.item;public class Items{'
        'public static final Item COAL=new Item("minecraft:coal",64,1600),'
        'COPPER_INGOT=new Item("minecraft:copper_ingot"),COPPER_BLOCK=new Item("minecraft:copper_block"),'
        'IRON_INGOT=new Item("minecraft:iron_ingot"),STICK=new Item("minecraft:stick");}'
    )
    stubs["net/minecraft/tags/TagKey.java"] = (
        'package net.minecraft.tags;public record TagKey<T>(net.minecraft.resources.ResourceLocation location){}'
    )
    stubs["net/minecraft/tags/ItemTags.java"] = (
        'package net.minecraft.tags;import net.minecraft.resources.ResourceLocation;import net.minecraft.world.item.Item;'
        'public class ItemTags{public static final Object LOGS=new Object(),PLANKS=new Object();'
        'public static TagKey<Item> create(ResourceLocation id){return new TagKey<>(id);}}'
    )
    stubs["net/minecraft/resources/ResourceLocation.java"] = (
        'package net.minecraft.resources;public record ResourceLocation(String namespace,String path){'
        'public static ResourceLocation fromNamespaceAndPath(String namespace,String path){return new ResourceLocation(namespace,path);}'
        'public String toString(){return "ResourceLocation[n="+namespace+", p="+path+"]";}}'
    )
    stack = stubs["net/minecraft/world/item/ItemStack.java"]
    anchor = "public boolean is(Item i){return item==i;}"
    if anchor not in stack:
        raise SystemExit("Goal 16A stub anchor missing: ItemStack.is(Item)")
    stubs["net/minecraft/world/item/ItemStack.java"] = stack.replace(
        anchor,
        anchor + 'public boolean is(net.minecraft.tags.TagKey<Item> tag){'
        'return !isEmpty()&&tag.location().namespace().equals("c")&&tag.location().path().equals("ingots")'
        '&&(item==Items.IRON_INGOT||item.id.startsWith("hbmsntm:ingot_"));}',
        1,
    )

    recipes = stubs["com/hbm/inventory/RecipesCommon.java"]
    anchor = 'public List<ItemStack> extractForJEI(){return List.of();}public ItemStack extractForCyclingDisplay(int t){return ItemStack.EMPTY;}'
    if anchor not in recipes:
        raise SystemExit("Goal 16A stub anchor missing: RecipesCommon.AStack display methods")
    recipes = recipes.replace(
        anchor,
        'public boolean matchesRecipe(ItemStack s,boolean ignore){return false;}public AStack copy(){return this;}'
        + anchor,
        1,
    )
    anchor = 'public ComparableStack(Item i,int n,int m){super(n);item=i;meta=m;}'
    if anchor not in recipes:
        raise SystemExit("Goal 16A stub anchor missing: ComparableStack constructor")
    recipes = recipes.replace(
        anchor,
        'public ComparableStack(Item i){this(i,1,-1);}public ComparableStack(Item i,int n){this(i,n,-1);}'
        + anchor
        + 'public boolean matchesRecipe(ItemStack s,boolean ignore){return s.is(item)&&(meta<0||MetaHelper.getMeta(s)==meta)&&(ignore||s.getCount()>=stacksize);}'
        + 'public AStack copy(){return new ComparableStack(item,stacksize,meta);}',
        1,
    )
    recipes = recipes.replace(
        'public ItemStack toStack(){return MetaHelper.newStack(item,stacksize,meta);}',
        'public ItemStack toStack(){return MetaHelper.newStack(item,stacksize,meta);}',
        1,
    )
    recipes = recipes.replace(
        'public static class ComparableStack extends AStack',
        'public static class TagStack extends AStack{public TagStack(Object tag){super(1);}public TagStack(Object tag,int n){super(n);}}'
        'public static class ComparableStack extends AStack',
        1,
    )
    stubs["com/hbm/inventory/RecipesCommon.java"] = recipes
    return stubs
