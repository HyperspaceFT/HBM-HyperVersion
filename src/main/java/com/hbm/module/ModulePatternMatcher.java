package com.hbm.module;

import com.hbm.items.component.NtmDataComponents;
import com.hbm.util.ItemStackUtil;
import net.minecraft.ChatFormatting;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;

import java.util.List;
import java.util.Objects;

/**
 * Original ModulePatternMatcher: one match mode per filter slot. A mode is "exact", "wildcard" or the id of an item tag, which
 * takes the place of the original's ore dictionary names. The original's bedrock ore mode is not ported (NEO has no bedrock ore
 * items).
 */
public class ModulePatternMatcher {

    public static final String MODE_EXACT = "exact";
    public static final String MODE_WILDCARD = "wildcard";

    public final String[] modes;

    public ModulePatternMatcher(int count) {
        this.modes = new String[count];
    }

    /** Original :68-84: "exact" for items with subtypes, read as items whose default stack carries the type component. */
    public void initPatternStandard(Level level, ItemStack stack, int i) {

        if(level.isClientSide) return;

        if(stack.isEmpty()) {
            modes[i] = null;
            return;
        }

        modes[i] = stack.getItem().getDefaultInstance().has(NtmDataComponents.META) ? MODE_EXACT : MODE_WILDCARD;
    }

    /** The ore dictionary prefixes of the original initPatternSmart (:41-45), in its order, as tag path prefixes. */
    private static final String[] SMART_PREFIXES = { "ingots", "storage_blocks", "dusts", "nuggets", "plates" };

    /**
     * Original :30-53 (the conveyor sorter's filter): the first tag of the kinds ingot, block, dust, nugget and plate, in that order,
     * becomes the mode; otherwise "exact" for items with subtypes and "wildcard" for the rest (the bedrock ore branch is not ported).
     * NEO has tags where the original has ore dictionary names. Only tags naming a material count, a path "ingots/iron" or the flat
     * "ingots_iron", never the bare parent "c:ingots": iron is in both, and the parent sorts first but would match every ingot where
     * the original picks "ingotIron". Within one kind the first tag id in sorted order wins.
     */
    public void initPatternSmart(Level level, ItemStack stack, int i) {

        if(level.isClientSide) return;

        if(stack.isEmpty()) {
            modes[i] = null;
            return;
        }

        List<String> names = getTagNames(stack);

        for(String prefix : SMART_PREFIXES) {
            for(String name : names) {
                String path = name.substring(name.indexOf(':') + 1);

                if(path.startsWith(prefix + "/") || path.startsWith(prefix + "_")) {
                    modes[i] = name;
                    return;
                }
            }
        }

        modes[i] = stack.getItem().getDefaultInstance().has(NtmDataComponents.META) ? MODE_EXACT : MODE_WILDCARD;
    }

    /**
     * Original :86-131: empty, exact, wildcard, then every tag of the pattern in order, then back to exact. When the current tag
     * mode is no longer among the pattern's tags (tags change with data packs) the original keeps it; NEO returns to exact.
     */
    public void nextMode(Level level, ItemStack pattern, int i) {

        if(level.isClientSide) return;

        if(pattern.isEmpty()) {
            modes[i] = null;
            return;
        }

        if(modes[i] == null) {
            modes[i] = MODE_EXACT;
        } else if(MODE_EXACT.equals(modes[i])) {
            modes[i] = MODE_WILDCARD;
        } else if(MODE_WILDCARD.equals(modes[i])) {

            List<String> names = getTagNames(pattern);
            modes[i] = names.isEmpty() ? MODE_EXACT : names.get(0);
        } else {

            List<String> names = getTagNames(pattern);
            int index = names.indexOf(modes[i]);
            modes[i] = index >= 0 && index < names.size() - 1 ? names.get(index + 1) : MODE_EXACT;
        }
    }

    /**
     * Original :133-151. Exact: the same item with the same type component and damage, other components are not compared (the
     * original compares item and metadata, not NBT). Wildcard: the same item. A tag mode: the input carries that tag. An empty mode
     * counts as exact and is written back, as in the original.
     */
    public boolean isValidForFilter(ItemStack filter, int index, ItemStack input) {

        String mode = modes[index];

        if(mode == null) {
            modes[index] = mode = MODE_EXACT;
        }

        return switch(mode) {
            case MODE_EXACT -> input.getItem() == filter.getItem()
                    && Objects.equals(input.get(NtmDataComponents.META), filter.get(NtmDataComponents.META))
                    && input.getDamageValue() == filter.getDamageValue();
            case MODE_WILDCARD -> input.getItem() == filter.getItem();
            default -> getTagNames(input).contains(mode);
        };
    }

    /** The item's tag ids, sorted so that cycling through them does not depend on the order the tag stream happens to give. */
    public static List<String> getTagNames(ItemStack stack) {
        List<String> names = ItemStackUtil.getTags(stack);
        names.sort(null);
        return names;
    }

    public void readFromNBT(CompoundTag tag) {

        for(int i = 0; i < modes.length; i++) {
            modes[i] = tag.contains("mode" + i) ? tag.getString("mode" + i) : null;
        }
    }

    public void writeToNBT(CompoundTag tag) {

        for(int i = 0; i < modes.length; i++) {
            if(modes[i] != null) {
                tag.putString("mode" + i, modes[i]);
            }
        }
    }

    public void serialize(RegistryFriendlyByteBuf buf) {
        for(String mode : modes) {
            buf.writeBoolean(mode != null);
            if(mode != null) buf.writeUtf(mode);
        }
    }

    public void deserialize(RegistryFriendlyByteBuf buf) {
        for(int i = 0; i < modes.length; i++) {
            modes[i] = buf.readBoolean() ? buf.readUtf() : null;
        }
    }

    /** Original :186-193, hardcoded English there. */
    public static Component getLabel(String mode) {
        return switch(mode) {
            case MODE_EXACT -> Component.translatable("gui.hbmsntm.filter.exact").withStyle(ChatFormatting.YELLOW);
            case MODE_WILDCARD -> Component.translatable("gui.hbmsntm.filter.wildcard").withStyle(ChatFormatting.YELLOW);
            default -> Component.translatable("gui.hbmsntm.filter.tag", mode).withStyle(ChatFormatting.YELLOW);
        };
    }
}
