"""Goal18A recipe world: the production CrystallizerRecipes contract, sync, client sync, packet and JEI handler over the
inherited Goal16A registry/component/Gson services (the Goal16B Block/Item identity adaptations are re-applied here because
the Goal16B adapter needs its frozen build/ baseline, which this worktree does not carry)."""
from goal16a_regression.recipe_stubs import recipe_stubs as base_stubs, RECIPE_SOURCES as BASE
from goal10b_regression.stubs import method_body

EXTRA = ('com/hbm/inventory/recipes/CrystallizerRecipes.java', 'com/hbm/inventory/recipes/CrystallizerRecipeSync.java',
         'com/hbm/handler/CrystallizerRecipeClientSync.java', 'com/hbm/network/toclient/CrystallizerRecipesPacket.java',
         'com/hbm/handler/jei/CrystallizerRecipeHandler.java')
RECIPE_SOURCES = tuple(dict.fromkeys((*BASE, *EXTRA)))

def recipe_stubs(source, extras):
    stubs = base_stubs(source, [(source / p).read_text(encoding='utf-8') for p in EXTRA] + extras)
    body = method_body((source / 'com/hbm/handler/jei/NtmJeiPlugin.java').read_text(encoding='utf-8'), 'private void refreshCrystallizerRecipes() {', 'production crystallizer JEI')
    stubs['goal18a/JeiBridge.java'] = '''package goal18a;import java.util.*;import com.hbm.inventory.recipes.CrystallizerRecipes;import com.hbm.handler.jei.CrystallizerRecipeHandler;
public class JeiBridge{public Manager runtime;public List<CrystallizerRecipes.CrystallizerRecipe> displayedCrystallizerRecipes=List.of();public final List<CrystallizerRecipes.CrystallizerRecipe> knownCrystallizerRecipes=new ArrayList<>();
public void available(){runtime=new Manager();com.hbm.handler.CrystallizerRecipeClientSync.setRefresh(this::refreshCrystallizerRecipes);refreshCrystallizerRecipes();}
public void unavailable(){com.hbm.handler.CrystallizerRecipeClientSync.setRefresh(null);displayedCrystallizerRecipes=List.of();knownCrystallizerRecipes.clear();runtime=null;}
public static class Manager{public int additions,hidden,unhidden;public Manager getRecipeManager(){return this;}public void hideRecipes(Object t,List<?> r){hidden+=r.size();}public void addRecipes(Object t,List<?> r){additions+=r.size();}public void unhideRecipes(Object t,List<?> r){unhidden+=r.size();}}
''' + body + '}'
    # Goal16B identity adaptations: blocks are Blocks with asItem(), registry-backed Item.create, ComparableStack(Block).
    stubs['net/minecraft/world/level/block/Block.java'] = 'package net.minecraft.world.level.block;public class Block implements net.minecraft.world.level.ItemLike{private final net.minecraft.world.item.Item item;public Block(String id){item=net.minecraft.world.item.Item.create(id);}public net.minecraft.world.item.Item asItem(){return item;}}'
    n = 'net/minecraft/world/level/block/Blocks.java'
    stubs[n] = stubs[n].replace('import net.minecraft.world.item.Item;', '').replace('final Item ', 'final Block ').replace('new Item(', 'new Block(')
    n = 'com/hbm/blocks/NtmBlocks.java'
    stubs[n] = stubs[n].replace('private final Item i;', 'private final net.minecraft.world.level.block.Block i;').replace('i=new Item(s);', 'i=new net.minecraft.world.level.block.Block(s);').replace('public Item get(){return i;}', 'public net.minecraft.world.level.block.Block get(){return i;}').replace('public Item asItem(){return i;}', 'public Item asItem(){return i.asItem();}')
    n = 'com/hbm/inventory/RecipesCommon.java'
    if 'ComparableStack(net.minecraft.world.level.block.Block b)' not in stubs[n]:
        stubs[n] = stubs[n].replace('public static class ComparableStack extends AStack{', 'public static class ComparableStack extends AStack{public ComparableStack(net.minecraft.world.level.block.Block b){this(b.asItem(),1,32767);}public ComparableStack(net.minecraft.world.level.block.Block b,int n){this(b.asItem(),n,32767);}')
    n = 'net/minecraft/world/item/Item.java'
    if 'public static Item create(' not in stubs[n]:
        stubs[n] = stubs[n].replace('public class Item implements ItemLike{', 'public class Item implements ItemLike{public static Item create(String id){String n=id.toLowerCase(java.util.Locale.ROOT);if(!n.contains(":"))n="hbmsntm:"+n;var key=net.minecraft.resources.ResourceLocation.parse(n);return BuiltInRegistries.ITEM.containsKey(key)?BuiltInRegistries.ITEM.get(key):new Item(n);}')
    n = 'net/minecraft/world/item/Items.java'
    stubs[n] = stubs[n].replace('new Item(', 'Item.create(')
    n = 'net/minecraft/client/gui/GuiGraphics.java'
    if 'public void blit(Object t,int a,int b,int c,int d,int e,int f,int g,int h)' not in stubs[n]:
        stubs[n] = stubs[n].replace('public class GuiGraphics{', 'public class GuiGraphics{public void blit(Object t,int a,int b,int c,int d,int e,int f,int g,int h){}')
    for p in RECIPE_SOURCES: stubs.pop(p, None)
    return stubs
