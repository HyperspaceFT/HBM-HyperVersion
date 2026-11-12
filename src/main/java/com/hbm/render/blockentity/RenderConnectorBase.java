package com.hbm.render.blockentity;

import com.hbm.blockentity.network.ConnectorBlockEntity;
import com.hbm.blockentity.network.ConnectorSuperBlockEntity;
import com.hbm.main.ResourceManager;
import com.hbm.render.util.RenderContext;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;

/**
 * Electricity connector and its heavy duty variant (original RenderConnector.java:14-62, RenderConnectorSuper.java:14-64). The
 * heavy duty type is registered with this class and the connector type with {@link RenderConnector}, which adds the item renderer
 * of both items once.
 */
public class RenderConnectorBase extends RenderPylonBase<ConnectorBlockEntity> {

    @Override public BlockEntityRenderer<ConnectorBlockEntity> create(Context context) { return new RenderConnectorBase(); }

    @Override
    public void render(ConnectorBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        RenderContext.pushPose();
        RenderContext.translate(0.5F, 0.5F, 0.5F);

        switch(be.getFacing()) {
            case DOWN -> RenderContext.mulPose(Axis.XP.rotationDegrees(180F));
            case NORTH -> { RenderContext.mulPose(Axis.XP.rotationDegrees(90F)); RenderContext.mulPose(Axis.ZP.rotationDegrees(180F)); }
            case SOUTH -> RenderContext.mulPose(Axis.XP.rotationDegrees(90F));
            case WEST -> { RenderContext.mulPose(Axis.XP.rotationDegrees(90F)); RenderContext.mulPose(Axis.ZP.rotationDegrees(90F)); }
            case EAST -> { RenderContext.mulPose(Axis.XP.rotationDegrees(90F)); RenderContext.mulPose(Axis.ZP.rotationDegrees(270F)); }
            default -> { }
        }

        RenderContext.translate(0F, -0.5F, 0F);

        boolean heavy = be instanceof ConnectorSuperBlockEntity;
        bindTexture(heavy ? ResourceManager.CONNECTOR_SUPER_TEX : ResourceManager.CONNECTOR_TEX);
        (heavy ? ResourceManager.connector_super : ResourceManager.connector).renderAll();

        RenderContext.popPose();

        this.renderLinesGeneric(be, buffer);
    }
}
