package com.hbm.blocks.network;

import com.hbm.blockentity.network.PylonLargeBlockEntity;
import com.mojang.serialization.MapCodec;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import java.util.List;

/**
 * Large electricity pylon, fourteen blocks tall on a 3x3 base (original PylonLarge.java:20-96). The tooltip asks for a substation,
 * which the original never enforces.
 */
public class PylonLargeBlock extends PylonDummyableBlock {

    public PylonLargeBlock(Properties properties) {
        super(properties);
    }

    @Override protected BlockEntity createPylon(BlockPos pos, BlockState state) { return new PylonLargeBlockEntity(pos, state); }

    @Override public int[] getDimensions() { return new int[] {13, 0, 1, 1, 1, 1}; }
    @Override public int getOffset() { return 0; }

    public static final MapCodec<PylonLargeBlock> CODEC = simpleCodec(PylonLargeBlock::new);
    @Override protected MapCodec<PylonLargeBlock> codec() { return CODEC; }

    /** The core faces in 45 degree steps of the player's yaw, four facings over a half turn (PylonLarge.java:62-83). */
    @Override
    protected BlockState getStateForCore(Level level, BlockPos pos, Player player, Direction dir) {
        int i = Mth.floor(player.getYRot() * 4.0F / 180.0F + 0.5D) & 3;
        Direction facing = switch(i) {
            case 1 -> Direction.EAST;
            case 2 -> Direction.SOUTH;
            case 3 -> Direction.WEST;
            default -> Direction.NORTH;
        };
        return this.createCoreState(facing);
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {
        PylonTooltip.add(components, "quadruple", 100);
        components.add(Component.translatable("block.hbmsntm.red_pylon_large.substation").withStyle(ChatFormatting.GOLD));
    }
}
