package com.hbm.render.entity.projectile;

import com.hbm.entity.projectile.StrayCog;
import com.hbm.main.ResourceManager;
import com.hbm.render.util.RenderContext;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;

@OnlyIn(Dist.CLIENT)
public class RenderStrayCog extends EntityRenderer<StrayCog> {

    public RenderStrayCog(EntityRendererProvider.Context context) { super(context); }

    @Override
    public void render(StrayCog cog, float entityYaw, float partialTicks, PoseStack poseStack, MultiBufferSource buffer, int packedLight) {
        RenderContext.setup(poseStack, packedLight, OverlayTexture.NO_OVERLAY);

        int orientation = cog.getOrientation();
        switch(orientation % 6) {
            case 3 -> RenderContext.mulPose(Axis.YP.rotationDegrees(0F));
            case 5 -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            case 2 -> RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            case 4 -> RenderContext.mulPose(Axis.YP.rotationDegrees(270F));
            default -> { }
        }

        RenderContext.translate(0.0F, 0.0F, -1.0F);

        // Orientations 6-11 mark a cog lying on the ground, which stops spinning.
        if(orientation < 6) {
            RenderContext.mulPose(Axis.ZN.rotationDegrees((float) (System.currentTimeMillis() % (360 * 3) / 3D)));
        }

        RenderContext.translate(0.0F, -1.375F, 0.0F);

        RenderSystem.setShaderTexture(0, this.getTextureLocation(cog));
        ResourceManager.stirling.renderPart("Cog");

        RenderContext.end();
    }

    @Override
    public ResourceLocation getTextureLocation(StrayCog cog) {
        return ResourceManager.STIRLING_TEX;
    }
}
