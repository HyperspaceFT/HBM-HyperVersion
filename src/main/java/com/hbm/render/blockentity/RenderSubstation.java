package com.hbm.render.blockentity;

import com.hbm.blockentity.network.SubstationBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

/** Substation (original RenderSubstation.java:11-41, item ItemRenderLibrary.java:943-953). */
public class RenderSubstation extends RenderPylonBase<SubstationBlockEntity> implements IBEWLRProvider {

    @Override public BlockEntityRenderer<SubstationBlockEntity> create(Context context) { return new RenderSubstation(); }

    @Override
    public void render(SubstationBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        RenderContext.pushPose();
        RenderContext.translate(0.5F, 0F, 0.5F);

        switch(be.getBlockState().getValue(DummyableBlock.FACING)) {
            case NORTH, SOUTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            default -> { }
        }

        bindTexture(ResourceManager.SUBSTATION_TEX);
        ResourceManager.substation.renderAll();

        RenderContext.popPose();

        this.renderLinesGeneric(be, buffer);
    }

    @Override
    public Item getItemForRenderer() {
        return NtmBlocks.SUBSTATION.asItem();
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -2.5F, 0F);
                RenderContext.scale(4.5F, 4.5F, 4.5F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.scale(0.5F, 0.5F, 0.5F);
                bindTexture(ResourceManager.SUBSTATION_TEX);
                ResourceManager.substation.renderAll();
            }
        };
    }
}
