"""Extend the 15B isolated world; mixer/coker/network classes stay production sources."""
from goal15b_regression.machine_stubs import machine_stubs as base_stubs, MACHINE_SOURCES as BASE
from goal10b_regression.stubs import method_body

EXTRA = ('com/hbm/blockentity/machine/MachineMixerBlockEntity.java',
         'com/hbm/inventory/menus/MachineMixerMenu.java',
         'com/hbm/inventory/recipes/MixerRecipes.java',
         'com/hbm/inventory/recipes/anvil/AnvilSmithingIngotMoldRecipe.java')
MACHINE_SOURCES = tuple(dict.fromkeys((*BASE, *EXTRA)))


def machine_stubs(source, extras, tags, jar):
    stubs = base_stubs(source, [(source / p).read_text(encoding='utf-8') for p in EXTRA] + extras, tags, jar)
    n = 'com/hbm/inventory/RecipesCommon.java'
    stubs[n] = stubs[n].replace('public static abstract class AStack{', 'public static abstract class AStack implements Comparable<AStack>{public int compareTo(AStack other){return 0;}public AStack copy(int amount){AStack s=copy();s.stacksize=amount;return s;}')
    n = 'net/minecraft/tags/ItemTags.java'
    stubs[n] = stubs[n].replace('public static Object create(net.minecraft.resources.ResourceLocation id){return id.n()+":"+id.p();}', 'public static net.minecraft.tags.TagKey<net.minecraft.world.item.Item> create(net.minecraft.resources.ResourceLocation id){return net.minecraft.tags.TagKey.create(null,id);}')
    n = 'net/minecraft/core/registries/BuiltInRegistries.java'
    stubs[n] = stubs[n].replace('public boolean containsKey(net.minecraft.resources.ResourceLocation id){return false;}public net.minecraft.world.item.Item get(net.minecraft.resources.ResourceLocation id){return null;}', '''private final java.util.Map<String,net.minecraft.world.item.Item> items=new java.util.HashMap<>();
public void bind(){if(!items.isEmpty())return;try{for(Class<?> c:new Class<?>[]{net.minecraft.world.item.Items.class,com.hbm.items.NtmItems.class,com.hbm.blocks.NtmBlocks.class})for(var f:c.getFields()){Object v=f.get(null);if(v instanceof net.minecraft.world.level.ItemLike like){var i=like.asItem();items.put(i.id,i);}else{try{Object item=v.getClass().getMethod("get").invoke(v);if(item instanceof net.minecraft.world.level.ItemLike like){var i=like.asItem();items.put(i.id,i);}}catch(ReflectiveOperationException ignored){}}}}catch(ReflectiveOperationException e){throw new RuntimeException(e);}}
public boolean containsKey(net.minecraft.resources.ResourceLocation id){bind();return items.containsKey(id.toString());}public net.minecraft.world.item.Item get(net.minecraft.resources.ResourceLocation id){bind();return items.get(id.toString());}
    public java.util.List<net.minecraft.core.Holder<net.minecraft.world.item.Item>> getTagOrEmpty(net.minecraft.tags.TagKey<net.minecraft.world.item.Item> t){bind();return items.values().stream().filter(i->i.tags.contains(t.location().toString())).map(i->(net.minecraft.core.Holder<net.minecraft.world.item.Item>)new net.minecraft.core.Holder.Direct<>(i)).toList();}
public java.util.Optional<java.util.List<net.minecraft.core.Holder<net.minecraft.world.item.Item>>> getTag(net.minecraft.tags.TagKey<net.minecraft.world.item.Item> t){var v=getTagOrEmpty(t);return v.isEmpty()?java.util.Optional.empty():java.util.Optional.of(v);}''')
    n = 'net/minecraft/world/item/ItemStack.java'
    stubs[n] = stubs[n].replace('return tag instanceof String s&&item!=null&&', 'String s=tag instanceof net.minecraft.tags.TagKey<?> key?key.location().toString():tag instanceof String text?text:null;return s!=null&&item!=null&&')
    n = 'com/hbm/blockentity/LoadedBaseBlockEntity.java'
    onload = method_body((source / n).read_text(encoding='utf-8'), 'public void onLoad() {', 'LoadedBaseBlockEntity').replace('super.onLoad();', '')
    stubs[n] = stubs[n].replace('public class LoadedBaseBlockEntity extends', 'public class LoadedBaseBlockEntity extends')
    stubs[n] = stubs[n].replace('public enum TiltType', onload + 'public enum TiltType')
    n = 'com/hbm/blocks/DummyableBlock.java'
    methods = '\n'.join(method_body((source / n).read_text(encoding='utf-8'), s, 'DummyableBlock') for s in ('public BlockState createDummyState(', 'public BlockState createExtraState('))
    stubs[n] = stubs[n].replace('public static final Object FACING', methods + 'public static final Object FACING')
    for path in MACHINE_SOURCES:
        stubs.pop(path, None)
    return stubs
