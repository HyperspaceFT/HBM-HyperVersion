package com.hbm.blocks.machine.rbmk;

import net.minecraft.world.level.block.Block;

/**
 * Original RBMKDebris ("pribris"): inert wreckage left by an RBMK meltdown. A full block for collision; it renders the
 * models/obj/rbmk/debris.obj shape (original RenderPribris) through its baked block model, so the properties carry noOcclusion.
 */
public class RBMKDebrisBlock extends Block {

    public RBMKDebrisBlock(Properties properties) {
        super(properties);
    }
}
