package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.MachineCrucibleBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.core.Direction;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

public class RenderCrucible extends BlockEntityRendererNT<MachineCrucibleBlockEntity> implements IBEWLRProvider {

    @Override public BlockEntityRenderer<MachineCrucibleBlockEntity> create(Context context) { return new RenderCrucible(); }

    @Override
    public void render(MachineCrucibleBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        RenderContext.translate(0.5F, 0.0F, 0.5F);
        Direction facing = be.getBlockState().getValue(DummyableBlock.FACING);
        switch(facing) {
            case NORTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            case SOUTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(270F));
            case WEST -> RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            case EAST -> RenderContext.mulPose(Axis.YP.rotationDegrees(0F));
        }
        bindTexture(ResourceManager.MACHINE_CRUCIBLE_TEX);
        ResourceManager.machine_crucible.renderAll();
    }

    @Override public Item getItemForRenderer() { return NtmBlocks.MACHINE_CRUCIBLE.asItem(); }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -1.5F, 0F);
                RenderContext.scale(3.25F, 3.25F, 3.25F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                bindTexture(ResourceManager.MACHINE_CRUCIBLE_TEX);
                ResourceManager.machine_crucible.renderAll();
            }
        };
    }
}
