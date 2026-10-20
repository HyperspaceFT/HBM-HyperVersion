package com.hbm.render.entity.projectile;

import com.hbm.entity.projectile.RBMKDebris;
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

/** Original RenderRBMKDebris: one OBJ and texture per debris type, spun like RenderZirnoxDebris. */
@OnlyIn(Dist.CLIENT)
public class RenderRBMKDebris extends EntityRenderer<RBMKDebris> {

    // glRotatef(angle, 1, 1, 1) in the original normalizes the axis.
    private static final Axis DIAGONAL = Axis.of(new Vector3f(1F, 1F, 1F).normalize());

    public RenderRBMKDebris(EntityRendererProvider.Context context) { super(context); }

    @Override
    public void render(RBMKDebris debris, float entityYaw, float partialTicks, PoseStack poseStack, MultiBufferSource buffer, int packedLight) {
        RenderContext.setup(poseStack, packedLight, OverlayTexture.NO_OVERLAY);

        RenderContext.translate(0.0F, 0.125F, 0.0F);

        RenderContext.mulPose(Axis.YP.rotationDegrees(debris.getId() % 360)); //rotate based on entity ID to add unique randomness
        RenderContext.mulPose(DIAGONAL.rotationDegrees(Mth.lerp(partialTicks, debris.lastRot, debris.rot)));

        ResourceLocation tex;
        IModelCustom model;
        switch(debris.getDebrisType()) {
            case ELEMENT -> { tex = ResourceManager.RBMK_DEB_BASE_TEX; model = ResourceManager.deb_element; }
            case FUEL -> { tex = ResourceManager.RBMK_DEB_ELEMENT_TEX; model = ResourceManager.deb_fuel; }
            case GRAPHITE -> { tex = ResourceManager.BLOCK_GRAPHITE_TEX; model = ResourceManager.deb_graphite; }
            case LID -> { tex = ResourceManager.RBMK_DEB_LID_TEX; model = ResourceManager.deb_lid; }
            case ROD -> { tex = ResourceManager.RBMK_DEB_CONTROL_TEX; model = ResourceManager.deb_rod; }
            default -> { tex = ResourceManager.RBMK_DEB_BLANK_TEX; model = ResourceManager.deb_blank; }
        }

        RenderSystem.disableCull();
        RenderSystem.setShaderTexture(0, tex);
        model.renderAll();
        RenderSystem.enableCull();

        RenderContext.end();
    }

    //for fallback only
    @Override
    public ResourceLocation getTextureLocation(RBMKDebris debris) {
        return ResourceManager.RBMK_DEB_BASE_TEX;
    }
}
