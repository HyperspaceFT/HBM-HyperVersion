package com.hbm.render.blockentity;

import com.hbm.blockentity.network.PylonBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.mojang.blaze3d.systems.RenderSystem;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

/** Wooden and steel pylon (original RenderPylon.java:15-80). */
public class RenderPylon extends RenderPylonBase<PylonBlockEntity> implements IBEWLRProvider {

    @Override public BlockEntityRenderer<PylonBlockEntity> create(Context context) { return new RenderPylon(); }

    @Override
    public void render(PylonBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        RenderContext.pushPose();
        RenderContext.translate(0.5F, 0F, 0.5F);
        RenderSystem.disableCull();

        boolean wood = be.getBlockState().is(NtmBlocks.RED_PYLON.get());
        bindTexture(wood ? ResourceManager.PYLON_TEX : ResourceManager.PYLON_STEEL_TEX);
        ResourceManager.pylon.renderPart(wood ? "Pylon" : "Pylon_steel");

        RenderSystem.enableCull();
        RenderContext.popPose();

        this.renderLinesGeneric(be, buffer);
    }

    @Override
    public Item[] getItemsForRenderer() {
        return new Item[] {NtmBlocks.RED_PYLON.asItem(), NtmBlocks.RED_PYLON_STEEL.asItem()};
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -5F, 0F);
                RenderContext.scale(2.9F, 2.9F, 2.9F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                boolean wood = stack.is(NtmBlocks.RED_PYLON.asItem());
                bindTexture(wood ? ResourceManager.PYLON_TEX : ResourceManager.PYLON_STEEL_TEX);
                ResourceManager.pylon.renderPart(wood ? "Pylon" : "Pylon_steel");
            }
        };
    }
}
