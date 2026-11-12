package com.hbm.render.blockentity;

import com.hbm.blockentity.network.NetworkSeparatorBlockEntity;
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
import net.minecraft.world.phys.AABB;

/** Network separator (original RenderNetworkSeparator.java:15-58). */
public class RenderNetworkSeparator extends BlockEntityRendererNT<NetworkSeparatorBlockEntity> implements IBEWLRProvider {

    @Override public BlockEntityRenderer<NetworkSeparatorBlockEntity> create(Context context) { return new RenderNetworkSeparator(); }

    @Override
    public void render(NetworkSeparatorBlockEntity separator, MultiBufferSource buffer, float partialTicks) {
        RenderContext.translate(0.5F, 0F, 0.5F);

        switch(separator.getBlockState().getValue(DummyableBlock.FACING)) {
            case NORTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            case WEST -> RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            case SOUTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(270F));
            default -> { }
        }

        bindTexture(ResourceManager.NETWORK_SEPARATOR_TEX);
        ResourceManager.network_separator.renderAll();
    }

    // BlockNetworkSeparator.java:314-320: one block around the core and two high
    @Override public AABB getRenderBoundingBox(NetworkSeparatorBlockEntity be) { return new AABB(be.getBlockPos()).inflate(1, 0, 1).expandTowards(0, 1, 0); }

    @Override
    public Item[] getItemsForRenderer() {
        return new Item[] {NtmBlocks.NETWORK_SEPARATOR.asItem()};
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -3F, 0F);
                RenderContext.scale(5F, 5F, 5F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                bindTexture(ResourceManager.NETWORK_SEPARATOR_TEX);
                ResourceManager.network_separator.renderAll();
            }
        };
    }
}
