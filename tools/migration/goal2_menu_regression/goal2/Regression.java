package goal2;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.menus.AnvilMenu;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilSmithingRecipe;
import com.hbm.network.toserver.AnvilConstructionPacket;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.MenuType;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.network.handling.IPayloadContext;

public final class Regression {
    private static int checks;

    private static void check(boolean condition, String message) {
        checks++;
        if(!condition) throw new AssertionError(message);
    }

    private static AnvilMenu menu(Player player, boolean shapeless, int outputCount) {
        AnvilRecipes.SMITHING.clear();
        AnvilSmithingRecipe recipe = new AnvilSmithingRecipe(1, new ItemStack("result", outputCount),
                new AStack("left", 2), new AStack("right", 1));
        AnvilRecipes.SMITHING.add(shapeless ? recipe.makeShapeless() : recipe);
        AnvilMenu menu = new AnvilMenu(1, player.inventory, new BlockPos(0, 0, 0), 1);
        player.containerMenu = menu;
        return menu;
    }

    private static Player player() {
        Level level = new Level();
        level.state = new BlockState(NtmBlocks.ANVIL.get(), 1);
        return new Player(level);
    }

    private static void inputs(AnvilMenu menu, String left, int leftCount, String right, int rightCount) {
        menu.slots.get(0).setByPlayer(new ItemStack(left, leftCount));
        menu.slots.get(1).setByPlayer(new ItemStack(right, rightCount));
        check(!menu.slots.get(2).getItem().isEmpty(), "recipe result should appear");
    }

    private static void normalClickConsumesEveryTime() {
        Player player = player();
        AnvilMenu menu = menu(player, false, 2);
        inputs(menu, "left", 4, "right", 2);
        for(int i = 0; i < 2; i++) {
            ItemStack taken = menu.be.removeItem(2, 2);
            menu.slots.get(2).onTake(player, taken);
            check(taken.getCount() == 2, "normal click result count");
            check(menu.be.getItem(0).getCount() == 2 - i * 2, "normal click left ingredient");
            check(menu.be.getItem(1).getCount() == 1 - i, "normal click right ingredient");
        }
        check(menu.be.getItem(2).isEmpty(), "normal click result ends when inputs exhausted");
        check(player.crafted == 4, "normal click crafting callback count");
    }

    private static void shiftClickConsumesEveryTime() {
        Player player = player();
        AnvilMenu menu = menu(player, false, 2);
        inputs(menu, "left", 4, "right", 2);
        check(menu.quickMoveStack(player, 2).getCount() == 2, "first shift-click result");
        check(menu.be.getItem(0).getCount() == 2, "first shift-click left deduction");
        check(menu.be.getItem(1).getCount() == 1, "first shift-click right deduction");
        check(menu.quickMoveStack(player, 2).getCount() == 2, "second shift-click result");
        check(menu.be.getItem(0).isEmpty() && menu.be.getItem(1).isEmpty(), "second deduction");
        check(menu.be.getItem(2).isEmpty(), "result empty after two crafts");
        check(player.crafted == 4, "shift-click crafting callback once per full output");
    }

    private static void partialCapacityNeverGrants() {
        Player player = player();
        AnvilMenu menu = menu(player, false, 2);
        inputs(menu, "left", 2, "right", 1);
        for(int i = 0; i < 36; i++) player.inventory.setItem(i, new ItemStack("filler", 64));
        player.inventory.setItem(0, new ItemStack("result", 63));
        check(menu.quickMoveStack(player, 2).isEmpty(), "partial space rejects full result");
        check(player.inventory.getItem(0).getCount() == 63, "partial space grants nothing");
        check(menu.be.getItem(0).getCount() == 2 && menu.be.getItem(1).getCount() == 1, "partial space consumes nothing");
        check(menu.be.getItem(2).getCount() == 2, "partial space leaves full result");
        player.inventory.setItem(0, new ItemStack("result", 62));
        check(menu.quickMoveStack(player, 2).getCount() == 2, "exact capacity transfers all");
        check(player.inventory.getItem(0).getCount() == 64, "exact capacity inventory count");
        check(menu.be.getItem(0).isEmpty() && menu.be.getItem(1).isEmpty(), "exact capacity consumes inputs");
    }

    private static void invalidIndexAndMirroredInputs() {
        Player player = player();
        AnvilMenu menu = menu(player, true, 1);
        check(menu.quickMoveStack(player, -1).isEmpty(), "negative slot index");
        check(menu.quickMoveStack(player, menu.slots.size()).isEmpty(), "oversized slot index");
        inputs(menu, "right", 1, "left", 2);
        check(menu.quickMoveStack(player, 2).getCount() == 1, "mirrored recipe output");
        check(menu.be.getItem(0).isEmpty() && menu.be.getItem(1).isEmpty(), "mirrored amounts deducted from proper slots");
    }

    private record Context(Player player) implements IPayloadContext {
        public void enqueueWork(Runnable work) { work.run(); }
    }

    private static void packetRequiresValidMenuAndMode() {
        Player player = player();
        AnvilMenu menu = menu(player, false, 1);
        AnvilRecipes.executionCount = 0;
        AnvilConstructionPacket.handleServer(new AnvilConstructionPacket(0, 0), new Context(player));
        check(AnvilRecipes.executionCount == 1, "valid construction reaches recipe executor");
        AnvilConstructionPacket.handleServer(new AnvilConstructionPacket(0, 1), new Context(player));
        check(AnvilRecipes.executionCount == 2 && AnvilRecipes.lastMode == 1, "valid bulk mode reaches executor");
        AnvilConstructionPacket.handleServer(new AnvilConstructionPacket(0, -1), new Context(player));
        AnvilConstructionPacket.handleServer(new AnvilConstructionPacket(0, 2), new Context(player));
        check(AnvilRecipes.executionCount == 2, "invalid modes rejected before executor");
        AnvilConstructionPacket.handleServer(new AnvilConstructionPacket(-1, 0), new Context(player));
        check(AnvilRecipes.executionCount == 2, "invalid recipe index rejected by recipe stub");

        player.level.state = new BlockState(new Object(), 1);
        check(!menu.stillValid(player), "removed anvil invalidates menu");
        AnvilConstructionPacket.handleServer(new AnvilConstructionPacket(0, 0), new Context(player));
        check(AnvilRecipes.executionCount == 2, "removed anvil blocks packet");
        player.level.state = new BlockState(NtmBlocks.ANVIL.get(), 2);
        check(!menu.stillValid(player), "replaced-tier anvil invalidates menu");
        AnvilConstructionPacket.handleServer(new AnvilConstructionPacket(0, 0), new Context(player));
        check(AnvilRecipes.executionCount == 2, "changed tier blocks packet");
        player.level.state = new BlockState(NtmBlocks.ANVIL.get(), 1);
        player.x = 10;
        check(!menu.stillValid(player), "distant player invalidates menu");
        AnvilConstructionPacket.handleServer(new AnvilConstructionPacket(0, 0), new Context(player));
        check(AnvilRecipes.executionCount == 2, "distant player blocks packet");
        player.x = .5;
        player.containerMenu = new AbstractContainerMenu(new MenuType<>(), 1) {
            public boolean stillValid(Player ignored) { return true; }
            public ItemStack quickMoveStack(Player ignored, int index) { return ItemStack.EMPTY; }
        };
        AnvilConstructionPacket.handleServer(new AnvilConstructionPacket(0, 0), new Context(player));
        check(AnvilRecipes.executionCount == 2, "wrong menu blocks packet");
    }

    public static void main(String[] args) {
        normalClickConsumesEveryTime();
        shiftClickConsumesEveryTime();
        partialCapacityNeverGrants();
        invalidIndexAndMirroredInputs();
        packetRequiresValidMenuAndMode();
        System.out.println("PASS " + checks + " menu/packet assertions");
    }
}
