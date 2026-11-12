package com.hbm.items.tools;

import com.hbm.blockentity.network.PylonBaseBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.main.NuclearTechMod;
import com.hbm.main.ServerProxy;
import com.hbm.util.TagsUtil;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.core.component.DataComponents;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntity;

import java.util.List;

/**
 * Cable drum (original ItemWiring.java:20-125): the first right-click on a pylon stores its core as the wire start, the second on
 * another pylon links both ends. Sneaking does nothing. The links are made on the server only; the client shows the distance to
 * the start while the drum is in the inventory.
 */
public class WiringItem extends Item {

    public WiringItem(Properties properties) {
        super(properties);
    }

    public static boolean hasStart(ItemStack stack) {
        CompoundTag tag = TagsUtil.getCustomData(stack);
        return tag.contains("x") && tag.contains("y") && tag.contains("z");
    }

    public static BlockPos getStart(ItemStack stack) {
        CompoundTag tag = TagsUtil.getCustomData(stack);
        return new BlockPos(tag.getInt("x"), tag.getInt("y"), tag.getInt("z"));
    }

    @Override
    public InteractionResult useOn(UseOnContext context) {
        Player player = context.getPlayer();
        if(player != null && player.isShiftKeyDown()) return InteractionResult.PASS;

        Level level = context.getLevel();
        BlockPos pos = context.getClickedPos();
        ItemStack stack = context.getItemInHand();

        Block b = level.getBlockState(pos).getBlock();
        if(b instanceof DummyableBlock dummy) {
            BlockPos core = dummy.findCore(level, pos);
            if(core != null) pos = core;
        }

        if(!(level.getBlockEntity(pos) instanceof PylonBaseBlockEntity second)) return InteractionResult.PASS;
        if(level.isClientSide) return InteractionResult.SUCCESS;

        if(!hasStart(stack)) {
            CompoundTag tag = new CompoundTag();
            tag.putInt("x", pos.getX());
            tag.putInt("y", pos.getY());
            tag.putInt("z", pos.getZ());
            TagsUtil.putCustomData(stack, tag);
            message(player, "start");
        } else {
            BlockPos start = getStart(stack);
            BlockEntity be = level.getBlockEntity(start);

            if(be instanceof PylonBaseBlockEntity first) {
                switch(PylonBaseBlockEntity.canConnect(first, second)) {
                    case 0 -> {
                        first.addConnection(pos);
                        second.addConnection(start);
                        message(player, "end");
                    }
                    case 1 -> message(player, "error_type");
                    case 2 -> message(player, "error_same");
                    case 3 -> message(player, "error_far");
                    default -> { }
                }
            } else {
                message(player, "error");
            }

            stack.remove(DataComponents.CUSTOM_DATA);
        }

        return InteractionResult.SUCCESS;
    }

    private void message(Player player, String key) {
        if(player != null) player.sendSystemMessage(Component.translatable(this.getDescriptionId() + "." + key));
    }

    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> components, TooltipFlag flag) {
        if(hasStart(stack)) {
            BlockPos start = getStart(stack);
            components.add(Component.translatable(this.getDescriptionId() + ".start_x", start.getX()));
            components.add(Component.translatable(this.getDescriptionId() + ".start_y", start.getY()));
            components.add(Component.translatable(this.getDescriptionId() + ".start_z", start.getZ()));
        } else {
            components.add(Component.translatable(this.getDescriptionId() + ".desc"));
        }
    }

    @Override
    public void inventoryTick(ItemStack stack, Level level, Entity entity, int slotId, boolean isSelected) {
        if(level.isClientSide && hasStart(stack)) {
            BlockPos start = getStart(stack);
            double dx = entity.getX() - start.getX();
            double dy = entity.getY() - start.getY();
            double dz = entity.getZ() - start.getZ();
            // ServerProxy holds the same info IDs as NuclearTechModClient without loading a client class
            NuclearTechMod.proxy.displayTooltip(Component.translatable(this.getDescriptionId() + ".distance", stack.getHoverName(), (int) Math.sqrt(dx * dx + dy * dy + dz * dz)), ServerProxy.ID_CABLE);
        }
    }
}
