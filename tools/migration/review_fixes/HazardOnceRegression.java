package hazardonce;

import java.util.*;
import java.util.function.*;

/**
 * Observation driver for the hazard-once review fix, method level and not a real Minecraft world. For every variant of
 * CommonEvents.onLivingTick it runs the side x kind scenarios and prints one OBS line each: how many times the player, living and dropped-item
 * hazard entry points and EntityEffectHandler.tick ran, and how often each held or worn stack was visited. It asserts nothing; the verifier
 * compares the lines with the table derived from the original, so a variant can also be shown to be wrong rather than only crash.
 */
final class HazardOnceRegression {
    private HazardOnceRegression() {}

    static final int[] SELECTED_SLOTS = {0, 4, 8};

    public static void main(String[] args) {
        for (Map.Entry<String, Consumer<EntityTickEvent.Pre>> variant : Variants.all().entrySet()) {
            for (boolean client : new boolean[] {false, true}) {
                for (int selected : SELECTED_SLOTS) player(variant, client, selected);
                pig(variant, client);
                item(variant, client);
                plain(variant, client);
            }
        }
    }

    static String side(boolean client) { return client ? "client" : "server"; }

    static void player(Map.Entry<String, Consumer<EntityTickEvent.Pre>> variant, boolean client, int selected) {
        Player player = new Player(new Level(client));
        Inventory inventory = player.getInventory();
        inventory.selected = selected;
        // Main hand = the selected hotbar stack; another hotbar slot and a main-inventory slot are visited by updatePlayerInventory only.
        ItemStack main = new ItemStack("main"), otherHotbar = new ItemStack("other_hotbar"), inv = new ItemStack("inv");
        ItemStack offhand = new ItemStack("offhand"), feet = new ItemStack("feet"), legs = new ItemStack("legs"), chest = new ItemStack("chest"), head = new ItemStack("head");
        inventory.items.set(selected, main);
        inventory.items.set((selected + 1) % 9, otherHotbar);
        inventory.items.set(20, inv);
        inventory.offhand.set(0, offhand);
        inventory.armor.set(0, feet);
        inventory.armor.set(1, legs);
        inventory.armor.set(2, chest);
        inventory.armor.set(3, head);
        run(variant, "player_" + side(client) + "_s" + selected, player, List.of(main, otherHotbar, inv, offhand, feet, legs, chest, head));
    }

    static void pig(Map.Entry<String, Consumer<EntityTickEvent.Pre>> variant, boolean client) {
        LivingEntity pig = new LivingEntity(new Level(client));
        ItemStack main = new ItemStack("main"), offhand = new ItemStack("offhand"), feet = new ItemStack("feet"), legs = new ItemStack("legs"), chest = new ItemStack("chest"), head = new ItemStack("head");
        pig.equipment[EquipmentSlot.MAINHAND.ordinal()] = main;
        pig.equipment[EquipmentSlot.OFFHAND.ordinal()] = offhand;
        pig.equipment[EquipmentSlot.FEET.ordinal()] = feet;
        pig.equipment[EquipmentSlot.LEGS.ordinal()] = legs;
        pig.equipment[EquipmentSlot.CHEST.ordinal()] = chest;
        pig.equipment[EquipmentSlot.HEAD.ordinal()] = head;
        run(variant, "pig_" + side(client), pig, List.of(main, offhand, feet, legs, chest, head));
    }

    static void item(Map.Entry<String, Consumer<EntityTickEvent.Pre>> variant, boolean client) {
        run(variant, "item_" + side(client), new ItemEntity(new Level(client)), List.of());
    }

    static void plain(Map.Entry<String, Consumer<EntityTickEvent.Pre>> variant, boolean client) {
        run(variant, "plain_" + side(client), new Entity(new Level(client)), List.of());
    }

    static void run(Map.Entry<String, Consumer<EntityTickEvent.Pre>> variant, String scenario, Entity entity, List<ItemStack> stacks) {
        HazardSystem.reset();
        variant.getValue().accept(new EntityTickEvent.Pre(entity));
        StringBuilder visits = new StringBuilder();
        for (ItemStack stack : stacks) {
            if (visits.length() > 0) visits.append(',');
            visits.append(stack.name).append(':').append(stack.visits);
        }
        System.out.println("OBS|" + variant.getKey() + "|" + scenario + "|player=" + HazardSystem.playerCalls + "|living=" + HazardSystem.livingCalls
                + "|dropped=" + HazardSystem.droppedCalls + "|effect=" + EntityEffectHandler.calls + "|visits=" + visits);
    }
}
