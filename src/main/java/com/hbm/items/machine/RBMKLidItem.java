package com.hbm.items.machine;

import com.hbm.blockentity.machine.rbmk.RBMKBaseBlockEntity;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock.LidType;
import net.minecraft.core.BlockPos;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.state.BlockState;

/** Original ItemRBMKLid: puts a concrete or lead glass lid on an RBMK column that has none. */
public class RBMKLidItem extends Item {

    private final LidType lid;

    public RBMKLidItem(Properties properties, LidType lid) {
        super(properties);
        this.lid = lid;
    }

    public LidType getLid() {
        return this.lid;
    }

    /** Original onItemUse (:21-66). */
    @Override
    public InteractionResult useOn(UseOnContext context) {
        Level level = context.getLevel();
        BlockPos pos = context.getClickedPos();

        if(!(level.getBlockState(pos).getBlock() instanceof RBMKBaseBlock rbmk)) return InteractionResult.PASS;

        BlockPos core = rbmk.findCore(level, pos);
        if(core == null) return InteractionResult.PASS;
        if(!(level.getBlockEntity(core) instanceof RBMKBaseBlockEntity tile)) return InteractionResult.PASS;
        if(tile.hasLid()) return InteractionResult.PASS;

        if(!level.isClientSide) {
            // The original plays the place sound of Blocks.glass or ModBlocks.concrete_smooth (a stone-sounding block).
            SoundType sound = this.lid == LidType.GLASS ? SoundType.GLASS : SoundType.STONE;
            level.playSound(null, pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5, sound.getPlaceSound(), SoundSource.BLOCKS, (sound.getVolume() + 1.0F) / 2.0F, sound.getPitch() * 0.8F);

            BlockState coreState = level.getBlockState(core);
            level.setBlock(core, coreState.setValue(RBMKBaseBlock.LID, this.lid), 3);
            context.getItemInHand().shrink(1);
            tile.onLidChanged();
        }

        return InteractionResult.sidedSuccess(level.isClientSide);
    }
}
