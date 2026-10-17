"""Bounded method-level world for the hazard-once review fix (Goal21D O1: CommonEvents.onLivingTick).

The live CommonEvents.onLivingTick text (and, for comparison, the frozen start form and each mutated form) is copied verbatim into one
compile shell per variant, together with the live HazardSystem.updatePlayerInventory / updateLivingInventory bodies. Everything the
methods touch is a minimal stand-in: Entity/LivingEntity/Player/ItemEntity with a Level whose isClientSide is a plain field, the
Player.getItemBySlot / Inventory layout of 1.21.1 (items(36), armor(4), offhand(1), selected hotbar slot; the verifier checks that layout
against the cached Minecraft sources), and a counting applyHazards. A GameTest cannot create a player, so this is the player-path
evidence; it is not a Minecraft launch, it does not prove the event is delivered on both logical sides (the verifier reads that from the
NeoForge javadoc) and the real APIs are checked by the main build.
"""


def strip_comments(text):
    """Java source without // and /* */ comments; string and char literals are kept intact."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def closing(text, opening):
    """Index of the brace closing the one at `opening`, skipping comments and string/char literals."""
    depth, i, n = 0, opening, len(text)
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        if c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        depth += (c == "{") - (c == "}")
        if depth == 0:
            return i
        i += 1
    raise ValueError("unbalanced braces")


def span(text, signature):
    start = text.index(signature)
    if text.find(signature, start + 1) >= 0:
        raise ValueError(f"ambiguous method: {signature}")
    return start, closing(text, text.index("{", start)) + 1


def method(text, signature):
    start, end = span(text, signature)
    return text[start:end]


EVENT_SIGNATURE = "public static void onLivingTick(EntityTickEvent.Pre event)"
PLAYER_SIGNATURE = "public static void updatePlayerInventory(Player player)"
LIVING_SIGNATURE = "public static void updateLivingInventory(LivingEntity entity)"

STUBS = r'''package hazardonce;
import java.util.*;
import java.util.function.*;

final class Level {
    public final boolean isClientSide;
    Level(boolean isClientSide) { this.isClientSide = isClientSide; }
}
class Entity {
    private final Level level;
    Entity(Level level) { this.level = level; }
    public Level level() { return level; }
}
enum EquipmentSlot {
    MAINHAND, OFFHAND, FEET, LEGS, CHEST, HEAD, BODY;
    // EquipmentSlot.getIndex for the humanoid armor slots (FEET 0 .. HEAD 3); MAINHAND, OFFHAND and BODY are not armor.
    boolean isArmor() { return this == FEET || this == LEGS || this == CHEST || this == HEAD; }
    int armorIndex() { return ordinal() - FEET.ordinal(); }
}
final class ItemStack {
    static final ItemStack EMPTY = new ItemStack("empty", true);
    final String name;
    final boolean empty;
    int visits;
    ItemStack(String name) { this(name, false); }
    private ItemStack(String name, boolean empty) { this.name = name; this.empty = empty; }
    boolean isEmpty() { return empty; }
}
class LivingEntity extends Entity {
    final ItemStack[] equipment = new ItemStack[EquipmentSlot.values().length];
    LivingEntity(Level level) { super(level); Arrays.fill(equipment, ItemStack.EMPTY); }
    ItemStack getItemBySlot(EquipmentSlot slot) { return equipment[slot.ordinal()]; }
}
final class Inventory {
    final List<ItemStack> items = new ArrayList<>(Collections.nCopies(36, ItemStack.EMPTY));
    final List<ItemStack> armor = new ArrayList<>(Collections.nCopies(4, ItemStack.EMPTY));
    final List<ItemStack> offhand = new ArrayList<>(Collections.nCopies(1, ItemStack.EMPTY));
    int selected;
    ItemStack getSelected() { return selected >= 0 && selected < 9 ? items.get(selected) : ItemStack.EMPTY; }
}
final class Player extends LivingEntity {
    private final Inventory inventory = new Inventory();
    Player(Level level) { super(level); }
    Inventory getInventory() { return inventory; }
    // Player.getItemBySlot (1.21.1, contract-checked): selected hotbar stack, offhand(0), armor(index), anything else empty.
    @Override ItemStack getItemBySlot(EquipmentSlot slot) {
        if (slot == EquipmentSlot.MAINHAND) return inventory.getSelected();
        if (slot == EquipmentSlot.OFFHAND) return inventory.offhand.get(0);
        return slot.isArmor() ? inventory.armor.get(slot.armorIndex()) : ItemStack.EMPTY;
    }
}
final class ItemEntity extends Entity { ItemEntity(Level level) { super(level); } }
final class EntityTickEvent {
    static final class Pre {
        private final Entity entity;
        Pre(Entity entity) { this.entity = entity; }
        Entity getEntity() { return entity; }
    }
}
final class EntityEffectHandler {
    static int calls;
    static void tick(LivingEntity entity) { calls++; }
}
// The live bodies of updatePlayerInventory and updateLivingInventory run behind counting entry points; applyHazards counts one visit per stack.
final class HazardSystem {
    static int playerCalls, livingCalls, droppedCalls;
    static void reset() { playerCalls = 0; livingCalls = 0; droppedCalls = 0; EntityEffectHandler.calls = 0; }
    static void applyHazards(ItemStack stack, LivingEntity entity) { stack.visits++; }
    static void updatePlayerInventory(Player player) { playerCalls++; updatePlayerInventoryBody(player); }
    static void updateLivingInventory(LivingEntity entity) { livingCalls++; updateLivingInventoryBody(entity); }
    static void updateDroppedItem(ItemEntity entity) { droppedCalls++; }
__BODIES__
}
__VARIANT_CLASSES__
final class Variants {
    static Map<String, Consumer<EntityTickEvent.Pre>> all() {
        Map<String, Consumer<EntityTickEvent.Pre>> map = new LinkedHashMap<>();
__VARIANT_ENTRIES__
        return map;
    }
}
'''


def indent(text, prefix="    "):
    return "\n".join(prefix + line if line.strip() else line for line in text.split("\n"))


def build_world(variants, hazard_text):
    """variants: ordered {name: onLivingTick method text}; hazard_text: the live HazardSystem.java text (LF)."""
    player = method(hazard_text, PLAYER_SIGNATURE).replace("updatePlayerInventory(", "updatePlayerInventoryBody(", 1)
    living = method(hazard_text, LIVING_SIGNATURE).replace("updateLivingInventory(", "updateLivingInventoryBody(", 1)
    classes, entries = [], []
    for index, (name, text) in enumerate(variants.items()):
        classes.append(f"final class V{index} {{\n{indent(text.strip(chr(10)))}\n}}")
        entries.append(f'        map.put("{name}", V{index}::onLivingTick);')
    return (STUBS.replace("__BODIES__", indent(player) + "\n" + indent(living))
            .replace("__VARIANT_CLASSES__", "\n".join(classes))
            .replace("__VARIANT_ENTRIES__", "\n".join(entries)))
