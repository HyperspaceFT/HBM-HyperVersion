package com.hbm.items.tools;

import com.hbm.blockentity.network.PipeAnchorBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.main.NuclearTechMod;
import com.hbm.main.ServerProxy;
import com.hbm.util.TagsUtil;
import net.minecraft.core.BlockPos;
import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.SwordItem;
import net.minecraft.world.item.Tier;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.phys.Vec3;

import java.util.List;

/**
 * Pipe wrench (original ItemWrench.java:21-147): a steel sword whose first right-click on a pipe anchor stores the anchor as the
 * pipe start and whose second, on another anchor, lays a pipe between both. Sneaking does nothing. Hitting a mob pushes it along
 * the attacker's view with an anvil sound.
 */
public class WrenchItem extends SwordItem {

    public WrenchItem(Tier tier, Properties properties) {
        super(tier, properties);
    }

    public static boolean hasStart(ItemStack stack) {
        CompoundTag tag = TagsUtil.getCustomData(stack);
        return tag.contains("x") && tag.contains("y") && tag.contains("z");
    }

    public static BlockPos getStart(ItemStack stack) {
        CompoundTag tag = TagsUtil.getCustomData(stack);
        return new BlockPos(tag.getInt("x"), tag.getInt("y"), tag.getInt("z"));
    }

    /** Status codes and messages of ItemWrench.java:48-93; code 1 needs the exhaust or pneumatic anchors, which are deferred. */
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

        if(!(level.getBlockEntity(pos) instanceof PipeAnchorBlockEntity second)) return InteractionResult.PASS;
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

            if(be instanceof PipeAnchorBlockEntity first) {
                switch(PipeAnchorBlockEntity.canConnect(first, second)) {
                    case 0 -> {
                        first.addConnection(pos);
                        second.addConnection(start);
                        message(player, "end");
                    }
                    case 2 -> message(player, "error_same");
                    case 3 -> message(player, "error_far");
                    case 4 -> message(player, "error_fluid");
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

    /**
     * Knocks the target half a block along the attacker's view (ItemWrench.java:104-120). Returning false skips postHurtEnemy, so a
     * hit costs no durability, as the original's override never reached ItemSword.hitEntity.
     */
    @Override
    public boolean hurtEnemy(ItemStack stack, LivingEntity target, LivingEntity attacker) {
        Vec3 look = attacker.getLookAngle();
        target.setDeltaMovement(target.getDeltaMovement().add(look.x * 0.5, look.y * 0.5, look.z * 0.5));
        target.hurtMarked = true;
        target.level().playSound(null, target.getX(), target.getY(), target.getZ(), SoundEvents.ANVIL_LAND, SoundSource.PLAYERS, 3.0F, 0.75F);
        return false;
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
            NuclearTechMod.proxy.displayTooltip(Component.translatable(this.getDescriptionId() + ".distance", stack.getHoverName(), (int) Math.sqrt(dx * dx + dy * dy + dz * dz)), ServerProxy.ID_WRENCH);
        }
    }
}
