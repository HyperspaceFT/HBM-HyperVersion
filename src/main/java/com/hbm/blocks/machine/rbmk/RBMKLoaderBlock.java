package com.hbm.blocks.machine.rbmk;

import api.hbm.fluidmk2.IFluidConnectorBlockMK2;
import com.hbm.blocks.ITooltipProvider;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.trait.FT_Coolable;
import com.hbm.inventory.fluid.trait.FT_Heatable;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.Block;

import java.util.List;

/**
 * Original RBMKLoader: the steam connector. Placed below a column (directly, or under the column's feedwater pipe), it moves the
 * column's ports around itself (RBMKBaseBlockEntity.getPortConnections); ducts connect to its top for heatable fluids and to its
 * other faces for coolable ones and perfluoromethyl. It holds no fluid itself.
 */
public class RBMKLoaderBlock extends Block implements IFluidConnectorBlockMK2, ITooltipProvider {

    public static final MapCodec<RBMKLoaderBlock> CODEC = simpleCodec(RBMKLoaderBlock::new);

    public RBMKLoaderBlock(Properties properties) {
        super(properties);
    }

    @Override protected MapCodec<RBMKLoaderBlock> codec() { return CODEC; }

    // dir is the connecting face of this block, as the original ForgeDirection (Library.canConnectFluid passes the machine's side).
    @Override
    public boolean canConnect(FluidType type, BlockGetter level, BlockPos pos, Direction dir) {
        if(dir == Direction.UP) return type.hasTrait(FT_Heatable.class);
        return type.hasTrait(FT_Coolable.class) || type == Fluids.PERFLUOROMETHYL;
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {
        this.addStandardInfo(components);
    }
}
