package com.hbm.items.machine;

import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.recipes.loader.GenericRecipes;
import com.hbm.items.EnumMultiItem;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.ItemUtils;
import net.minecraft.world.level.Level;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * The original ItemBlueprintFolder (blueprint booklet): opening one gives a blueprint for a random pool of its kind.
 * Meta 0 draws from the alt. pools, 1 from discover., 2 from secret.
 */
public class BlueprintFolderItem extends EnumMultiItem {

    // Meta order is the original's damage values; the lower-case names give the textures blueprint_folder.<name>.png
    public enum Type {
        ALT(GenericRecipes.POOL_PREFIX_ALT),
        DISCOVER(GenericRecipes.POOL_PREFIX_DISCOVER),
        SECRET(GenericRecipes.POOL_PREFIX_SECRET);

        public final String poolPrefix;

        Type(String poolPrefix) {
            this.poolPrefix = poolPrefix;
        }
    }

    public BlueprintFolderItem(Properties properties) {
        super(properties, Type.class, false, true);
    }

    /** Original getSubItems: only the alt and discover booklets, not the secret one. */
    @Override
    public void getSubItems(Item item, List<ItemStack> stacks) {
        stacks.add(MetaHelper.newStack(item, Type.ALT));
        stacks.add(MetaHelper.newStack(item, Type.DISCOVER));
    }

    /**
     * Original ItemBlueprintFolder.onItemRightClick, server side only: if any pool has the booklet's prefix, one booklet is
     * used up and a blueprint for one of those pools, chosen uniformly over the pools (not their recipes), goes into the
     * inventory or is dropped. Without such a pool nothing happens and nothing is used up.
     */
    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand);
        // The server decides; consuming here keeps the client from also trying the other hand's item.
        if(level.isClientSide) return InteractionResultHolder.consume(stack);

        List<String> pools = getPools(MetaHelper.getMeta(stack));
        if(pools.isEmpty()) return InteractionResultHolder.pass(stack);

        String chosen = pools.get(player.getRandom().nextInt(pools.size()));
        ItemStack blueprint = BlueprintsItem.make(chosen);

        // ItemUtils.createFilledResult uses up one booklet (not in creative, as the original's tryUseItem restores the
        // count there) and, when the held stack is gone, hands the blueprint back as the held stack; adding it to the
        // inventory first could put it into the emptied hand slot, which useItem then clears. Otherwise it goes into the
        // inventory or is dropped, as the original.
        return InteractionResultHolder.consume(ItemUtils.createFilledResult(stack, player, blueprint, false));
    }

    /**
     * The registered pools a booklet of this meta draws from. The original iterates a HashMap's keys; they are sorted here
     * so the draw does not depend on hash order. An unknown meta has no pools, as in the original.
     */
    public static List<String> getPools(int meta) {
        List<String> pools = new ArrayList<>();
        Type[] types = Type.values();
        if(meta < 0 || meta >= types.length) return pools;

        String prefix = types[meta].poolPrefix;
        for(String pool : GenericRecipes.blueprintPools.keySet()) {
            if(pool.startsWith(prefix)) pools.add(pool);
        }
        Collections.sort(pools);
        return pools;
    }
}
