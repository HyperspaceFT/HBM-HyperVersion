package com.hbm.inventory;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.Container;
import net.minecraft.world.entity.ExperienceOrb;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.SmeltingRecipe;
import net.neoforged.neoforge.event.EventHooks;

/**
 * Output slot that pays furnace experience for the items a player takes, like upstream's (Minecraft 1.7.10) SlotSmelting:
 * the experience is looked up by the result item, not by the recipes the machine ran. Automation gets no experience.
 */
public class SlotSmeltingOutput extends Slot {

    private final Player player;
    private int removeCount;

    public SlotSmeltingOutput(Player player, Container container, int slot, int x, int y) {
        super(container, slot, x, y);
        this.player = player;
    }

    @Override
    public boolean mayPlace(ItemStack stack) {
        return false;
    }

    @Override
    public ItemStack remove(int amount) {
        if(this.hasItem()) {
            this.removeCount += Math.min(amount, this.getItem().getCount());
        }
        return super.remove(amount);
    }

    @Override
    public void onTake(Player player, ItemStack stack) {
        this.checkTakeAchievements(stack);
        super.onTake(player, stack);
    }

    @Override
    protected void onQuickCraft(ItemStack stack, int amount) {
        this.removeCount += amount;
        this.checkTakeAchievements(stack);
    }

    /** A hotbar-key swap takes the stack without remove(); upstream's swap went through decrStackSize and paid for it. */
    @Override
    protected void onSwapCraft(int amount) {
        this.removeCount += amount;
    }

    @Override
    protected void checkTakeAchievements(ItemStack stack) {
        stack.onCraftedBy(this.player.level(), this.player, this.removeCount);

        if(this.player instanceof ServerPlayer serverPlayer && this.removeCount > 0) {
            ServerLevel level = serverPlayer.serverLevel();
            awardExperience(level, serverPlayer, this.removeCount, getSmeltingExperience(level, stack));
        }

        this.removeCount = 0;
        EventHooks.firePlayerSmeltedEvent(this.player, stack);
    }

    /** The experience of the first smelting recipe whose result is this item, or 0. */
    public static float getSmeltingExperience(ServerLevel level, ItemStack result) {
        for(RecipeHolder<SmeltingRecipe> holder : level.getRecipeManager().getAllRecipesFor(RecipeType.SMELTING)) {
            if(ItemStack.isSameItem(holder.value().getResultItem(level.registryAccess()), result)) {
                return holder.value().getExperience();
            }
        }
        return 0F;
    }

    /**
     * Upstream SlotSmelting: nothing for 0; below 1 per item the whole part always and the fraction as a chance;
     * 1 or more per item pays exactly 1 per item (Minecraft 1.21's furnace would pay the full value).
     */
    private static void awardExperience(ServerLevel level, Player player, int count, float experience) {
        int amount;
        if(experience == 0F) {
            amount = 0;
        } else if(experience < 1F) {
            amount = Mth.floor(count * experience);
            float fraction = Mth.frac(count * experience);
            if(fraction != 0F && Math.random() < fraction) {
                amount++;
            }
        } else {
            amount = count;
        }

        if(amount > 0) {
            ExperienceOrb.award(level, player.position(), amount);
        }
    }
}
