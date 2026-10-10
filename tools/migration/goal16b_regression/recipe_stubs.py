"""Goal16A registry/component services with unchanged centrifuge production and frozen baseline."""
from goal16a_regression.recipe_stubs import recipe_stubs as base_stubs, RECIPE_SOURCES as BASE
from goal10b_regression.stubs import method_body
EXTRA=('com/hbm/inventory/recipes/CentrifugeRecipes.java','com/hbm/inventory/recipes/CentrifugeRecipeSync.java','com/hbm/handler/CentrifugeRecipeClientSync.java','com/hbm/network/toclient/CentrifugeRecipesPacket.java','com/hbm/handler/jei/CentrifugeRecipeHandler.java')
RECIPE_SOURCES=tuple(dict.fromkeys((*BASE,*EXTRA)))
def recipe_stubs(source,extras):
    frozen=source.parents[2]/'build/migration/goal16b/baseline-files/src/main/java/com/hbm/inventory/recipes/CentrifugeRecipes.java'
    text=frozen.read_text(encoding='utf-8').replace('CentrifugeRecipes','FrozenCentrifugeRecipes')
    stubs=base_stubs(source,[(source/p).read_text(encoding='utf-8') for p in EXTRA]+[text]+extras)
    stubs['com/hbm/inventory/recipes/FrozenCentrifugeRecipes.java']=text
    body=method_body((source/'com/hbm/handler/jei/NtmJeiPlugin.java').read_text(encoding='utf-8'),'private void refreshCentrifugeRecipes() {','production centrifuge JEI')
    stubs['goal16b/JeiBridge.java']='''package goal16b;import java.util.*;import com.hbm.inventory.recipes.CentrifugeRecipes;import com.hbm.handler.jei.CentrifugeRecipeHandler;public class JeiBridge{public Manager runtime;public List<CentrifugeRecipes.CentrifugeRecipe> displayedCentrifugeRecipes=List.of();public final List<CentrifugeRecipes.CentrifugeRecipe> knownCentrifugeRecipes=new ArrayList<>();public void available(){runtime=new Manager();com.hbm.handler.CentrifugeRecipeClientSync.setRefresh(this::refreshCentrifugeRecipes);refreshCentrifugeRecipes();}public void unavailable(){com.hbm.handler.CentrifugeRecipeClientSync.setRefresh(null);displayedCentrifugeRecipes=List.of();knownCentrifugeRecipes.clear();runtime=null;}public static class Manager{public int additions;public Manager getRecipeManager(){return this;}public void hideRecipes(Object t,List<?> r){}public void addRecipes(Object t,List<?> r){additions+=r.size();}public void unhideRecipes(Object t,List<?> r){}}'''+body+'}'
    stubs['net/minecraft/world/level/block/Block.java']='package net.minecraft.world.level.block;public class Block implements net.minecraft.world.level.ItemLike{private final net.minecraft.world.item.Item item;public Block(String id){item=new net.minecraft.world.item.Item(id);}public net.minecraft.world.item.Item asItem(){return item;}}'
    n='net/minecraft/world/level/block/Blocks.java'
    stubs[n]=stubs[n].replace('import net.minecraft.world.item.Item;','').replace('final Item ','final Block ').replace('new Item(','new Block(')
    n='com/hbm/blocks/NtmBlocks.java'
    stubs[n]=stubs[n].replace('private final Item i;','private final net.minecraft.world.level.block.Block i;').replace('i=new Item(s);','i=new net.minecraft.world.level.block.Block(s);').replace('public Item get(){return i;}','public net.minecraft.world.level.block.Block get(){return i;}').replace('public Item asItem(){return i;}','public Item asItem(){return i.asItem();}')
    n='com/hbm/inventory/RecipesCommon.java'
    stubs[n]=stubs[n].replace('public static class ComparableStack extends AStack{','public static class ComparableStack extends AStack{public ComparableStack(net.minecraft.world.level.block.Block b){this(b.asItem(),1,32767);}')
    n='net/minecraft/world/item/Item.java'
    stubs[n]=stubs[n].replace('public class Item implements ItemLike{','public class Item implements ItemLike{public static Item create(String id){String n=id.toLowerCase(java.util.Locale.ROOT);if(!n.contains(":"))n="hbmsntm:"+n;var key=net.minecraft.resources.ResourceLocation.parse(n);return BuiltInRegistries.ITEM.containsKey(key)?BuiltInRegistries.ITEM.get(key):new Item(n);}')
    n='net/minecraft/world/item/Items.java'
    stubs[n]=stubs[n].replace('new Item(','Item.create(')
    n='net/minecraft/world/level/block/Block.java'
    stubs[n]=stubs[n].replace('new net.minecraft.world.item.Item(id)','net.minecraft.world.item.Item.create(id)')
    n='net/minecraft/client/gui/GuiGraphics.java'
    stubs[n]=stubs[n].replace('public class GuiGraphics{','public class GuiGraphics{public void blit(Object t,int a,int b,int c,int d,int e,int f,int g,int h){}')
    for p in RECIPE_SOURCES:stubs.pop(p,None)
    return stubs