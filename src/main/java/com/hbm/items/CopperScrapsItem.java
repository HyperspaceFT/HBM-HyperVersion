package com.hbm.items;

import com.hbm.inventory.material.MaterialShapes;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.NTMMaterial;
import com.hbm.util.TagsUtil;
import net.minecraft.ChatFormatting;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;

import java.util.List;
import java.util.Locale;

/**
 * Preserves partial pours when a casting device is emptied or broken (upstream ItemScraps).
 * Goal 5A introduced it for copper only; Goal 10A accepts every registered crucible material.
 * The class name is kept so the Goal 5A casting regression still compiles it by name.
 */
public class CopperScrapsItem extends Item {
    public static final int MAX_AMOUNT = MaterialShapes.BLOCK.q(16);
    /**
     * Solid scraps with their own model, in override order: every smeltable or additive material (upstream
     * ItemScraps.getSubItems) in registration order. Upstream recolours one base texture per material at runtime;
     * NEO ships those recolours as textures (see {@link #getTextureName}). Copper keeps the Goal 5A base model.
     */
    public static final List<NTMMaterial> MODEL_MATERIALS = Mats.orderedList.stream()
            .filter(material -> material != Mats.MAT_COPPER && isScrapMaterial(material)).toList();
    public static final float ADDITIVE_LIQUID_MODEL = 0.75F;
    public static final float LIQUID_MODEL = 1F;

    public CopperScrapsItem(Properties properties) {
        super(properties);
    }

    public static ItemStack create(Mats.MaterialStack contents) {
        return create(contents, false);
    }

    /** Liquid scraps only exist as display stacks, like upstream's NEI handlers; they melt like solid scraps. */
    public static ItemStack create(Mats.MaterialStack contents, boolean liquid) {
        if(contents == null || contents.material == null || contents.amount <= 0) return ItemStack.EMPTY;
        ItemStack stack = new ItemStack(NtmItems.SCRAPS.get());
        CompoundTag tag = new CompoundTag();
        tag.putInt("material", contents.material.id);
        tag.putInt("amount", contents.amount);
        if(liquid) tag.putBoolean("liquid", true);
        TagsUtil.putCustomData(stack, tag);
        return stack;
    }

    /** Returns a copy of the stored material, or null for an empty, unknown or out-of-range stack. */
    public static Mats.MaterialStack getMats(ItemStack stack) {
        if(stack.isEmpty() || !stack.is(NtmItems.SCRAPS.get())) return null;
        CompoundTag tag = TagsUtil.getCustomData(stack);
        NTMMaterial material = Mats.matById.get(tag.getInt("material"));
        int amount = tag.getInt("amount");
        if(material == null || amount <= 0 || amount > MAX_AMOUNT) return null;
        return new Mats.MaterialStack(material, amount);
    }

    /** Materials upstream lists as scraps: smeltable or additive ones. */
    public static boolean isScrapMaterial(NTMMaterial material) {
        return material.smeltable == NTMMaterial.SmeltingBehavior.SMELTABLE || material.smeltable == NTMMaterial.SmeltingBehavior.ADDITIVE;
    }

    /**
     * Item model override value: 0 for the base model, {@link #getModelValue(int)} per material, 0.75 for liquid
     * additive and 1 for other liquid display stacks.
     */
    public static float getModelType(ItemStack stack) {
        Mats.MaterialStack contents = getMats(stack);
        if(contents == null) return 0F;
        if(isLiquid(stack)) return contents.material.smeltable == NTMMaterial.SmeltingBehavior.ADDITIVE ? ADDITIVE_LIQUID_MODEL : LIQUID_MODEL;
        int index = MODEL_MATERIALS.indexOf(contents.material);
        return index < 0 ? 0F : getModelValue(index);
    }

    /** Exact binary fractions below {@link #ADDITIVE_LIQUID_MODEL} for up to 191 materials. */
    public static float getModelValue(int index) {
        return (index + 1) / 256F;
    }

    public static String getModelName(NTMMaterial material) {
        return "scraps_" + material.names[0].toLowerCase(Locale.US);
    }

    /** Solid texture: upstream's bismuth override, the uncoloured base where light and dark match, else the recolour. */
    public static String getTextureName(NTMMaterial material) {
        if(material == Mats.MAT_BISMUTH) return "scraps_bismuth";
        if(material.solidColorLight == material.solidColorDark) return "scraps_plain";
        return getModelName(material);
    }

    /**
     * Liquid display stacks are tinted with the molten colour, as upstream does. Solid stacks on the uncoloured base
     * texture get the molten colour too (upstream ItemAutogen tints every material it did not recolour).
     */
    public static int getColor(ItemStack stack) {
        Mats.MaterialStack contents = getMats(stack);
        if(contents == null) return 0xFFFFFF;
        if(isLiquid(stack)) return contents.material.moltenColor;
        boolean plain = contents.material != Mats.MAT_COPPER && isScrapMaterial(contents.material)
                && "scraps_plain".equals(getTextureName(contents.material));
        return plain ? contents.material.moltenColor : 0xFFFFFF;
    }

    public static boolean isLiquid(ItemStack stack) {
        return stack.is(NtmItems.SCRAPS.get()) && TagsUtil.getCustomData(stack).getBoolean("liquid");
    }

    @Override
    public Component getName(ItemStack stack) {
        Mats.MaterialStack contents = getMats(stack);
        if(contents == null) return Component.translatable(this.getDescriptionId() + ".generic");
        if(isLiquid(stack)) return contents.material.getName();
        return Component.translatable(this.getDescriptionId(), contents.material.getName());
    }

    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltip, TooltipFlag flag) {
        Mats.MaterialStack contents = getMats(stack);
        if(contents == null) return;
        tooltip.add(Component.translatable("casting.scraps", contents.material.getName(), contents.amount));
        if(!isLiquid(stack)) tooltip.add(Component.translatable("casting.scraps.desc"));
        else if(contents.material.smeltable == NTMMaterial.SmeltingBehavior.ADDITIVE) {
            tooltip.add(Component.translatable("casting.scraps.additive").withStyle(ChatFormatting.DARK_RED));
        }
    }
}
