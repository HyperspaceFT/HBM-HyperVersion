package com.hbm.items.tools;

import com.hbm.extprop.HbmPlayerAttachments;
import com.hbm.handler.HbmKeybinds.EnumKeybind;
import com.hbm.interfaces.ICopiable;
import com.hbm.network.toclient.InformPlayer;
import com.hbm.util.Either;
import com.hbm.util.TagsUtil;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.StringTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.neoforged.neoforge.network.PacketDistributor;

import javax.annotation.Nullable;
import java.util.List;

/**
 * Original ItemSettingsTool: sneak right-click copies a machine's settings ({@link ICopiable}) onto the tool, right-click pastes them,
 * and the TOOL_ALT key cycles which of the copied entries a paste uses. The copy lives in the item's custom data, as the
 * multi fluid identifier keeps its types (GOAL31 decision 7): the source's settings plus "tileName", "copyIndex" and "displayInfo".
 */
public class SettingsToolItem extends Item {

    /** The first InformPlayer slot of the display entries, as in the original (:55). */
    public static final int INFORM_ID = 897;
    /** Original :37-42: Alt switches the entry at most every 5 ticks. */
    public static final int SWITCH_DELAY = 5;

    public SettingsToolItem(Properties properties) {
        super(properties);
    }

    /**
     * Original onUpdate (:29-62), on the server for the tool in the main hand: TOOL_ALT moves to the next entry, wrapping around,
     * and every 5 ticks the entries are shown, the current one aqua and the others yellow, for 4 seconds. The original counts a delay
     * up in the item's data every tick; a data change makes 1.21 resend the item, so NEO only writes when the entry changes and keeps
     * the game time of the last switch ("lastSwitch") instead.
     */
    @Override
    public void inventoryTick(ItemStack stack, Level level, Entity entity, int slot, boolean selected) {
        if(!(entity instanceof ServerPlayer player) || player.getMainHandItem() != stack || !TagsUtil.hasCustomData(stack)) return;

        CompoundTag data = TagsUtil.getCustomData(stack);
        ListTag info = data.getList("displayInfo", Tag.TAG_COMPOUND);
        long now = level.getGameTime();

        if(info.size() > 1 && HbmPlayerAttachments.getData(player).getKeyPressed(EnumKeybind.TOOL_ALT) && now - data.getLong("lastSwitch") >= SWITCH_DELAY) {
            int index = data.getInt("copyIndex") + 1;
            if(index > info.size() - 1) index = 0;
            data.putInt("copyIndex", index);
            data.putLong("lastSwitch", now);
            TagsUtil.putCustomData(stack, data);
        }

        if(now % 5 != 0) return;

        int current = data.getInt("copyIndex");

        for(int j = 0; j < info.size(); j++) {
            ChatFormatting format = current == j ? ChatFormatting.AQUA : ChatFormatting.YELLOW;
            Component line = Component.translatable(info.getCompound(j).getString("info")).withStyle(format);
            PacketDistributor.sendToPlayer(player, new InformPlayer(line, INFORM_ID + j, 4000));
        }
    }

    /** Original addInformation (:64-79), its hardcoded English now language keys. */
    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> tooltip, TooltipFlag flag) {
        tooltip.add(Component.translatable(this.getDescriptionId() + ".desc1"));
        tooltip.add(Component.translatable(this.getDescriptionId() + ".desc2"));
        tooltip.add(Component.translatable(this.getDescriptionId() + ".desc3"));

        if(TagsUtil.hasCustomData(stack)) {
            CompoundTag data = TagsUtil.getCustomData(stack);

            if(data.contains("tileName", Tag.TAG_STRING)) {
                tooltip.add(Component.translatable(data.getString("tileName")).withStyle(ChatFormatting.BLUE));
            } else {
                tooltip.add(Component.translatable(this.getDescriptionId() + ".none").withStyle(ChatFormatting.RED));
            }
        }
    }

    /**
     * Original onItemUseFirst (:81-122), which runs before the block's own right-click, so pasting onto a machine, a crane or a valve
     * neither opens its screen nor toggles it. NEO copies and pastes on the server only; the client answers success so the arm swings.
     * Blocks that cannot be copied pass on to their normal right-click.
     */
    @Override
    public InteractionResult onItemUseFirst(ItemStack stack, UseOnContext context) {
        Level level = context.getLevel();
        BlockPos pos = context.getClickedPos();
        Player player = context.getPlayer();
        if(player == null) return InteractionResult.PASS;

        Either<BlockEntity, Block> source = getCopyInfoSource(level, pos);
        if(source == null) return InteractionResult.PASS;
        if(level.isClientSide) return InteractionResult.SUCCESS;

        ICopiable copiable = source.cast();

        if(player.isShiftKeyDown()) {
            this.copy(stack, copiable, source, level, pos, player);
        } else if(TagsUtil.hasCustomData(stack)) {
            paste(stack, copiable, level, pos, player);
        }

        return InteractionResult.CONSUME;
    }

    /**
     * Original :86-115: the settings become the tool's whole data. Only null means the machine cannot be copied: the old data is then
     * cleared, as the original does (:87); an empty compound is a successful copy. The source name is already a full translation key
     * in NEO (ICopiable.getSettingsSourceID), so ".name" is not appended.
     */
    private void copy(ItemStack stack, ICopiable copiable, Either<BlockEntity, Block> source, Level level, BlockPos pos, Player player) {
        CompoundTag settings = copiable.getSettings(level, pos);
        Component name = Component.translatable(copiable.getSettingsSourceDisplay(source));

        if(settings == null) {
            stack.remove(DataComponents.CUSTOM_DATA);
            player.sendSystemMessage(this.prefix().append(Component.translatable(this.getDescriptionId() + ".copy_failed", name).withStyle(ChatFormatting.RED)));
            return;
        }

        CompoundTag data = settings.copy();
        data.putString("tileName", copiable.getSettingsSourceID(source));
        data.putInt("copyIndex", 0);
        data.putLong("lastSwitch", level.getGameTime());

        String[] info = copiable.infoForDisplay(level, pos);

        if(info != null) {
            ListTag display = new ListTag();

            for(String str : info) {
                CompoundTag entry = new CompoundTag();
                entry.put("info", StringTag.valueOf(str));
                display.add(entry);
            }

            data.put("displayInfo", display);
        }

        TagsUtil.putCustomData(stack, data);
        player.sendSystemMessage(this.prefix().append(Component.translatable(this.getDescriptionId() + ".copied", name).withStyle(ChatFormatting.AQUA)));
    }

    /**
     * Original :117-120 pastes on both sides without any check. NEO pastes on the server only (GOAL31 decision 6), after the block
     * right-click's own distance check: the target's chunk must be loaded, the player must be allowed to change the position, and the
     * entry index is clamped to at least 0. The data is player-writable; each implementor checks the keys it reads.
     */
    public static boolean paste(ItemStack stack, ICopiable copiable, Level level, BlockPos pos, Player player) {
        if(level.isClientSide || !level.hasChunkAt(pos) || !player.mayBuild() || !level.mayInteract(player, pos)) return false;

        CompoundTag data = TagsUtil.getCustomData(stack);
        int index = Math.max(0, data.getInt("copyIndex"));
        copiable.pasteSettings(data, index, level, player, pos);
        return true;
    }

    private MutableComponent prefix() {
        return Component.literal("[").withStyle(ChatFormatting.DARK_AQUA)
                .append(Component.translatable(this.getDescriptionId()).withStyle(ChatFormatting.DARK_AQUA))
                .append(Component.literal("] ").withStyle(ChatFormatting.DARK_AQUA));
    }

    /** Original :124-138: the block entity first, then the block. */
    @Nullable
    public static Either<BlockEntity, Block> getCopyInfoSource(Level level, BlockPos pos) {
        BlockEntity be = level.getBlockEntity(pos);
        if(be instanceof ICopiable) return Either.left(be);

        Block block = level.getBlockState(pos).getBlock();
        if(block instanceof ICopiable) return Either.right(block);

        return null;
    }
}
