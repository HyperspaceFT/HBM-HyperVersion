package com.hbm.particle;

import com.hbm.main.NuclearTechMod;
import com.hbm.particle.engine.ParticleNT;
import com.hbm.render.NtmRenderTypes;
import com.mojang.blaze3d.vertex.DefaultVertexFormat;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.blaze3d.vertex.VertexFormat;
import com.mojang.math.Axis;
import net.minecraft.client.Camera;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.FogRenderer;
import net.minecraft.client.renderer.RenderStateShard;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix4f;

/**
 * Original ParticleRBMKSteam: the steam jet a full steam channel vents from its top ("rbmksteam" aux particle). A 20-frame strip
 * on a camera-facing quad, additive, without depth writes, fog or lighting.
 */
public class RBMKSteamParticle extends ParticleNT {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/particle_no_sheet/rbmk_jet_steam.png");

    // Original GL state: blend SRC_ALPHA / ONE, depth mask off, lighting off; brightness 240 (the shader has no lightmap).
    private static final RenderType STEAM = RenderType.create(
            "rbmk_steam_render_type", DefaultVertexFormat.POSITION_TEX_COLOR, VertexFormat.Mode.QUADS, 1024,
            RenderType.CompositeState.builder()
                    .setShaderState(NtmRenderTypes.POSITION_TEX_COLOR)
                    .setTextureState(new RenderStateShard.TextureStateShard(TEXTURE, false, false))
                    .setTransparencyState(RenderType.LIGHTNING_TRANSPARENCY)
                    .setCullState(RenderStateShard.NO_CULL)
                    .setWriteMaskState(RenderStateShard.COLOR_WRITE)
                    .setOutputState(RenderStateShard.TRANSLUCENT_TARGET)
                    .createCompositeState(false)
    );

    public RBMKSteamParticle(ClientLevel level, double x, double y, double z) {
        super(level, x, y, z);

        this.lifetime = 10;
        this.alpha = 0.25F;
        this.quadSize = 4F;
    }

    // The original EntityFX does not move without motion; only the age advances.
    @Override
    public void tick() {
        this.xo = this.x;
        this.yo = this.y;
        this.zo = this.z;

        if(this.age++ >= this.lifetime) this.dead = true;
    }

    @Override
    public void render(VertexConsumer consumer, Camera camera, float partialTicks) {

        FogRenderer.setupNoFog();

        // The original clamps particleAge itself while rendering; a local gives the same frame.
        int age = Math.min(this.age, this.lifetime);

        // Upstream-shared: the - 1 makes the first frame index -1, sampling one frame left of the strip.
        int texIndex = (int) (((double) age / (double) this.lifetime) * 20) % 20 - 1;
        float f0 = 1F / 20F;

        float uMin = texIndex * f0;
        float uMax = uMin + f0;
        float vMin = 0;
        float vMax = 1;

        Vec3 camPos = camera.getPosition();
        float pX = (float) (Mth.lerp(partialTicks, this.xo, this.x) - camPos.x);
        float pY = (float) (Mth.lerp(partialTicks, this.yo, this.y) - camPos.y);
        float pZ = (float) (Mth.lerp(partialTicks, this.zo, this.z) - camPos.z);

        PoseStack poseStack = new PoseStack();
        poseStack.pushPose();
        poseStack.translate(pX, pY, pZ);
        poseStack.mulPose(Axis.YP.rotation((float) Math.toRadians(-camera.getYRot())));

        Matrix4f matrix = poseStack.last().pose();

        consumer.addVertex(matrix, this.quadSize * -0.25F - 0.9375F, -0.25F, 0).setUv(uMax, vMax).setColor(1.0F, 1.0F, 1.0F, this.alpha);
        consumer.addVertex(matrix, this.quadSize * -0.25F - 0.9375F, this.quadSize - 0.25F, 0).setUv(uMax, vMin).setColor(1.0F, 1.0F, 1.0F, this.alpha);
        consumer.addVertex(matrix, this.quadSize * 0.25F - 0.9375F, this.quadSize - 0.25F, 0).setUv(uMin, vMin).setColor(1.0F, 1.0F, 1.0F, this.alpha);
        consumer.addVertex(matrix, this.quadSize * 0.25F - 0.9375F, -0.25F, 0).setUv(uMin, vMax).setColor(1.0F, 1.0F, 1.0F, this.alpha);

        poseStack.popPose();
    }

    @Override public RenderType getRenderType() { return STEAM; }
}
