package com.hbm.render.entity.projectile;

import com.hbm.entity.projectile.ZirnoxDebris;
import com.hbm.main.ResourceManager;
import com.hbm.render.loader.IModelCustom;
import com.hbm.render.util.RenderContext;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import org.joml.Vector3f;

@OnlyIn(Dist.CLIENT)
public class RenderZirnoxDebris extends EntityRenderer<ZirnoxDebris> {

    // glRotatef(angle, 1, 1, 1) in the original normalizes the axis.
    private static final Axis DIAGONAL = Axis.of(new Vector3f(1F, 1F, 1F).normalize());

    public RenderZirnoxDebris(EntityRendererProvider.Context context) { super(context); }

    @Override
    public void render(ZirnoxDebris debris, float entityYaw, float partialTicks, PoseStack poseStack, MultiBufferSource buffer, int packedLight) {
        RenderContext.setup(poseStack, packedLight, OverlayTexture.NO_OVERLAY);

        RenderContext.translate(0.0F, 0.125F, 0.0F);

        RenderContext.mulPose(Axis.YP.rotationDegrees(debris.getId() % 360)); //rotate based on entity ID to add unique randomness
        RenderContext.mulPose(DIAGONAL.rotationDegrees(Mth.lerp(partialTicks, debris.lastRot, debris.rot)));

        ResourceLocation tex;
        IModelCustom model;
        switch(debris.getDebrisType()) {
            case ELEMENT -> { tex = ResourceManager.ZIRNOX_DEB_ELEMENT_TEX; model = ResourceManager.deb_zirnox_element; }
            case SHRAPNEL -> { tex = ResourceManager.ZIRNOX_TEX; model = ResourceManager.deb_zirnox_shrapnel; }
            case GRAPHITE -> { tex = ResourceManager.BLOCK_GRAPHITE_TEX; model = ResourceManager.deb_graphite; }
            case CONCRETE -> { tex = ResourceManager.ZIRNOX_DESTROYED_TEX; model = ResourceManager.deb_zirnox_concrete; }
            case EXCHANGER -> { tex = ResourceManager.ZIRNOX_TEX; model = ResourceManager.deb_zirnox_exchanger; }
            default -> { tex = ResourceManager.ZIRNOX_TEX; model = ResourceManager.deb_zirnox_blank; }
        }

        RenderSystem.disableCull();
        RenderSystem.setShaderTexture(0, tex);
        model.renderAll();
        RenderSystem.enableCull();

        RenderContext.end();
    }

    //for fallback only
    @Override
    public ResourceLocation getTextureLocation(ZirnoxDebris debris) {
        return ResourceManager.BLOCK_GRAPHITE_TEX;
    }
}
