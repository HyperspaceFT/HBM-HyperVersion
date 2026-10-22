package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.rbmk.RBMKAutoloaderBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

/**
 * Original RenderRBMKAutoloader: the loader body and the piston lowered by up to four blocks. The view distance is the base's 256
 * blocks, the original's 65536 squared.
 */
public class RenderRBMKAutoloader extends BlockEntityRendererNT<RBMKAutoloaderBlockEntity> implements IBEWLRProvider {

    @Override public BlockEntityRenderer<RBMKAutoloaderBlockEntity> create(Context context) { return new RenderRBMKAutoloader(); }

    @Override
    public void render(RBMKAutoloaderBlockEntity be, MultiBufferSource buffer, float partialTicks) {

        RenderContext.translate(0.5F, 0F, 0.5F);

        bindTexture(ResourceManager.RBMK_AUTOLOADER_TEX);
        ResourceManager.rbmk_autoloader.renderPart("Base");

        double p = be.lastPiston + (be.renderPiston - be.lastPiston) * partialTicks;
        RenderContext.translate(0F, (float) (p * -4D), 0F);

        RenderContext.translate(0F, 4F, 0F);
        ResourceManager.rbmk_autoloader.renderPart("Piston");
    }

    @Override
    public AABB getRenderBoundingBox(RBMKAutoloaderBlockEntity be) {
        return be.getRenderBoundingBox();
    }

    @Override
    public Item getItemForRenderer() {
        return NtmBlocks.RBMK_AUTOLOADER.asItem();
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -6F, 0F);
                RenderContext.scale(1.75F, 1.75F, 1.75F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
                RenderSystem.disableCull();
                bindTexture(ResourceManager.RBMK_AUTOLOADER_TEX);
                ResourceManager.rbmk_autoloader.renderPart("Base");
                ResourceManager.rbmk_autoloader.renderPart("Piston");
                RenderSystem.enableCull();
            }
        };
    }
}
