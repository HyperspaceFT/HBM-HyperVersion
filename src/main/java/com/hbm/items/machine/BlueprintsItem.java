package com.hbm.items.machine;

import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipes;
import com.hbm.items.IMetaItem;
import com.hbm.items.NtmItems;
import com.hbm.util.TagsUtil;
import net.minecraft.ChatFormatting;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;

import javax.annotation.Nullable;
import java.util.List;
import java.util.Map.Entry;

public class BlueprintsItem extends Item implements IMetaItem {

    /** Item model override values for the "blueprint_type" predicate; 0 is the base (blue) model, as the original's default icon */
    public static final float MODEL_DISCOVER = 1F;
    public static final float MODEL_SECRET = 2F;
    public static final float MODEL_528 = 3F;

    public BlueprintsItem(Properties properties) {
        super(properties);
    }

    @Override
    public void getSubItems(Item item, List<ItemStack> stacks) {
        for(Entry<String, List<String>> pool : GenericRecipes.blueprintPools.entrySet()) {
            String poolName = pool.getKey();
            if(!poolName.startsWith(GenericRecipes.POOL_PREFIX_SECRET)) stacks.add(make(poolName));
        }
    }

    /**
     * Original ItemBlueprints.onItemRightClick: copies the blueprint for one paper, server side only. Secret blueprints
     * cannot be copied. Outside creative the held stack grows by one if it can, otherwise the copy goes into the inventory
     * or is dropped; in creative a copy is dropped (the paper is still used up).
     */
    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand);
        // The server decides; consuming here keeps the client from also trying the other hand's item.
        if(level.isClientSide) return InteractionResultHolder.consume(stack);

        String poolName = grabPool(stack);
        if(poolName == null) return InteractionResultHolder.pass(stack);
        if(poolName.startsWith(GenericRecipes.POOL_PREFIX_SECRET)) return InteractionResultHolder.pass(stack);
        if(!consumePaper(player.getInventory())) return InteractionResultHolder.pass(stack);

        ItemStack copy = stack.copyWithCount(1);

        if(!player.getAbilities().instabuild) {
            if(stack.getCount() < stack.getMaxStackSize()) {
                stack.grow(1);
            } else if(!player.getInventory().add(copy)) {
                // Inventory.add may have shrunk the copy, so drop a fresh one, as the original does
                player.drop(stack.copyWithCount(1), false);
            }
        } else {
            player.drop(copy, false);
        }

        // A success result makes the server swing the hand for everyone, the original's swingItem
        return InteractionResultHolder.success(stack);
    }

    /** Original consumeInventoryItem(Items.paper): the first paper in the main inventory, if there is one. */
    private static boolean consumePaper(Inventory inventory) {
        for(ItemStack slot : inventory.items) {
            if(slot.is(Items.PAPER)) {
                slot.shrink(1);
                return true;
            }
        }
        return false;
    }

    /** Original ItemBlueprints.addInformation: whether the blueprint can be copied, then the name of each recipe in its pool. */
    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltipComponents, TooltipFlag tooltipFlag) {
        String poolName = grabPool(stack);
        if(poolName == null) return;

        List<String> pool = GenericRecipes.blueprintPools.get(poolName);
        if(pool == null || pool.isEmpty()) return;

        if(poolName.startsWith(GenericRecipes.POOL_PREFIX_SECRET)) {
            tooltipComponents.add(Component.translatable("item.hbmsntm.blueprints.no_copy").withStyle(ChatFormatting.RED));
        } else {
            tooltipComponents.add(Component.translatable("item.hbmsntm.blueprints.copy").withStyle(ChatFormatting.YELLOW));
        }

        for(String name : pool) {
            GenericRecipe recipe = GenericRecipes.pooledBlueprints.get(name);
            // Same name as the recipe selector shows (GenericRecipe.print)
            if(recipe != null) tooltipComponents.add(recipe.getName());
        }
    }

    /** Item model override value by pool prefix, as the original's icon: blue for any other pool (alt. included) or none. */
    public static float getModelType(ItemStack stack) {
        String poolName = grabPool(stack);
        if(poolName == null) return 0F;
        if(poolName.startsWith(GenericRecipes.POOL_PREFIX_DISCOVER)) return MODEL_DISCOVER; // beige
        if(poolName.startsWith(GenericRecipes.POOL_PREFIX_SECRET)) return MODEL_SECRET; // black
        if(poolName.startsWith(GenericRecipes.POOL_PREFIX_528)) return MODEL_528; // grey
        return 0F; // blue
    }

    @Nullable
    public static String grabPool(ItemStack stack) {
        if(stack.isEmpty()) return null;
        if(stack.getItem() != NtmItems.BLUEPRINTS.get()) return null;
        if(!TagsUtil.hasCustomData(stack)) return null;

        CompoundTag tag = TagsUtil.getCustomData(stack);
        if(!tag.contains("pool")) return null;
        return tag.getString("pool");
    }

    public static ItemStack make(String pool) {
        ItemStack stack = new ItemStack(NtmItems.BLUEPRINTS.get());
        CompoundTag tag = new CompoundTag();
        tag.putString("pool", pool);
        TagsUtil.putCustomData(stack, tag);
        return stack;
    }
}
