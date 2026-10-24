package com.hbm.render.model.armor;

import com.hbm.main.NuclearTechMod;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.model.geom.ModelLayerLocation;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.CubeListBuilder;
import net.minecraft.client.model.geom.builders.LayerDefinition;
import net.minecraft.client.model.geom.builders.MeshDefinition;
import net.minecraft.client.model.geom.builders.PartDefinition;
import net.minecraft.world.entity.LivingEntity;

/**
 * Original render/model/ModelM65 (Techne export, 10.08.2018, ZeuX), used by the M65, the half mask and the leather mask.
 * "mask" and "filter" are children of the head; the client extension toggles {@link #filter} by the installed filter.
 * The original sets mirror after addBox, which leaves the boxes unmirrored, so no cube is mirrored here.
 */
public class ModelM65 extends HumanoidModel<LivingEntity> {

    public static final ModelLayerLocation LAYER = new ModelLayerLocation(NuclearTechMod.withDefaultNamespace("gas_mask_m65"), "main");

    private static final float Y_OFFSET = 0.5F;

    public final ModelPart filter;

    public ModelM65(ModelPart root) {
        super(root);
        this.filter = this.head.getChild("filter");
    }

    public static LayerDefinition createLayer() {
        MeshDefinition mesh = new MeshDefinition();
        PartDefinition root = mesh.getRoot();

        PartDefinition head = root.addOrReplaceChild("head", CubeListBuilder.create(), PartPose.ZERO);
        root.addOrReplaceChild("hat", CubeListBuilder.create(), PartPose.ZERO);
        root.addOrReplaceChild("body", CubeListBuilder.create(), PartPose.ZERO);
        root.addOrReplaceChild("right_arm", CubeListBuilder.create(), PartPose.ZERO);
        root.addOrReplaceChild("left_arm", CubeListBuilder.create(), PartPose.ZERO);
        root.addOrReplaceChild("right_leg", CubeListBuilder.create(), PartPose.ZERO);
        root.addOrReplaceChild("left_leg", CubeListBuilder.create(), PartPose.ZERO);

        PartDefinition mask = head.addOrReplaceChild("mask", CubeListBuilder.create(), PartPose.ZERO);
        PartDefinition filter = head.addOrReplaceChild("filter", CubeListBuilder.create(), PartPose.ZERO);

        mask.addOrReplaceChild("mask_head", CubeListBuilder.create().texOffs(0, 0).addBox(0F, 0F, 0F, 8, 8, 8),
                PartPose.offsetAndRotation(-4F, -8F + Y_OFFSET, -4F, 0F, 0F, 0F));
        mask.addOrReplaceChild("nose", CubeListBuilder.create().texOffs(0, 16).addBox(0F, 0F, 0F, 3, 3, 1),
                PartPose.offsetAndRotation(-1.5F, -3.5F + Y_OFFSET, -5F, 0F, 0F, 0F));
        mask.addOrReplaceChild("outlet", CubeListBuilder.create().texOffs(0, 20).addBox(0F, -2F, 0F, 2, 2, 1),
                PartPose.offsetAndRotation(-1F, -3.5F + Y_OFFSET, -5F, -0.4799655F, 0F, 0F));
        mask.addOrReplaceChild("nose_slope", CubeListBuilder.create().texOffs(8, 16).addBox(0F, 0F, -2F, 3, 2, 2),
                PartPose.offsetAndRotation(-1.5F, -2F + Y_OFFSET, -4F, 0.6108652F, 0F, 0F));
        mask.addOrReplaceChild("eye1", CubeListBuilder.create().texOffs(0, 23).addBox(0F, 0F, 0F, 3, 3, 0),
                PartPose.offsetAndRotation(-3.5F, -6F + Y_OFFSET, -4.2F, 0F, 0F, 0F));
        mask.addOrReplaceChild("eye2", CubeListBuilder.create().texOffs(0, 26).addBox(0F, 0F, 0F, 3, 3, 0),
                PartPose.offsetAndRotation(0.5F, -6F + Y_OFFSET, -4.2F, 0F, 0F, 0F));
        mask.addOrReplaceChild("i_forgot", CubeListBuilder.create().texOffs(6, 20).addBox(0F, 0F, 0F, 2, 2, 1),
                PartPose.offsetAndRotation(-1F, -3.2F + Y_OFFSET, -6F, 0F, 0F, 0F));

        filter.addOrReplaceChild("filter_connector", CubeListBuilder.create().texOffs(6, 23).addBox(0F, 0F, -3F, 2, 2, 1),
                PartPose.offsetAndRotation(-1F, -2F + Y_OFFSET, -4F, 0.6108652F, 0F, 0F));
        filter.addOrReplaceChild("filter1", CubeListBuilder.create().texOffs(18, 21).addBox(0F, -1F, -5F, 3, 4, 2),
                PartPose.offsetAndRotation(-1.5F, -2F + Y_OFFSET, -4F, 0.6108652F, 0F, 0F));
        filter.addOrReplaceChild("filter2", CubeListBuilder.create().texOffs(18, 16).addBox(0F, -0.5F, -5F, 4, 3, 2),
                PartPose.offsetAndRotation(-2F, -2F + Y_OFFSET, -4F, 0.6108652F, 0F, 0F));

        return LayerDefinition.create(mesh, 32, 32);
    }

    // Original ModelM65.render: only the mask and, when visible, the filter are drawn
    @Override
    public void renderToBuffer(PoseStack poseStack, VertexConsumer buffer, int packedLight, int packedOverlay, int color) {
        poseStack.pushPose();

        if(this.young) {
            float f6 = 2.0F;
            poseStack.scale(1.5F / f6, 1.5F / f6, 1.5F / f6);
            poseStack.translate(0.0F, 16.0F / 16.0F, 0.0F);
            float d = 1F / 16F * 18F;
            poseStack.scale(d, d, d);
        } else {
            float d = 1F / 16F * 18F;
            poseStack.scale(d, d, d);
        }

        poseStack.scale(1.01F, 1.01F, 1.01F);
        this.head.render(poseStack, buffer, packedLight, packedOverlay, color);
        poseStack.popPose();
    }
}
