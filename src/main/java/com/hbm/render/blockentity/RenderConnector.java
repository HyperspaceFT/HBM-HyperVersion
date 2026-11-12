package com.hbm.render.blockentity;

import com.hbm.blockentity.network.ConnectorBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

/** The connector renderer that also provides the item renderer of both connectors (original RenderConnector.java:44-62, RenderConnectorSuper.java:44-64). */
public class RenderConnector extends RenderConnectorBase implements IBEWLRProvider {

    @Override public BlockEntityRenderer<ConnectorBlockEntity> create(Context context) { return new RenderConnector(); }

    @Override
    public Item[] getItemsForRenderer() {
        return new Item[] {NtmBlocks.RED_CONNECTOR.asItem(), NtmBlocks.RED_CONNECTOR_SUPER.asItem()};
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                boolean heavy = stack.is(NtmBlocks.RED_CONNECTOR_SUPER.asItem());
                RenderContext.translate(0F, heavy ? -5F : -3.5F, 0F);
                RenderContext.scale(7F, 7F, 7F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                boolean heavy = stack.is(NtmBlocks.RED_CONNECTOR_SUPER.asItem());
                RenderContext.scale(2F, 2F, 2F);
                bindTexture(heavy ? ResourceManager.CONNECTOR_SUPER_TEX : ResourceManager.CONNECTOR_TEX);
                (heavy ? ResourceManager.connector_super : ResourceManager.connector).renderAll();
            }
        };
    }
}
