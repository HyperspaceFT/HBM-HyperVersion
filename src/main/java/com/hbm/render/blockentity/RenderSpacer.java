package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.oil.FractionSpacerBlockEntity;
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
import net.minecraft.world.phys.AABB;

public class RenderSpacer extends BlockEntityRendererNT<FractionSpacerBlockEntity> implements IBEWLRProvider {

    @Override public BlockEntityRenderer<FractionSpacerBlockEntity> create(Context context) { return new RenderSpacer(); }

    @Override
    public void render(FractionSpacerBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        RenderContext.translate(0.5F, 0F, 0.5F);
        // The original separator does not rotate with the multiblock's placement direction.
        RenderSystem.enableCull();
        bindTexture(ResourceManager.fraction_spacer_tex);
        ResourceManager.fraction_spacer.renderAll();
    }

    @Override public AABB getRenderBoundingBox(FractionSpacerBlockEntity be) { return be.getRenderBoundingBox(); }
    @Override public int getViewDistance() { return 256; }
    @Override public Item getItemForRenderer() { return NtmBlocks.FRACTION_SPACER.asItem(); }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.scale(3.25F, 3.25F, 3.25F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                bindTexture(ResourceManager.fraction_spacer_tex);
                ResourceManager.fraction_spacer.renderAll();
            }
        };
    }
}
