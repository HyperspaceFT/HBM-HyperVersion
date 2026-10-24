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
 * Original render/model/ModelGasMask (Techne export, 23.12.2015, ZeuX). The shapes hang off the head through a "mask"
 * child, so the head pose copied from the wearer moves them like the original mask renderer followed bipedHead.
 * The original sets mirror after addBox, which leaves the boxes unmirrored, so no cube is mirrored here.
 */
public class ModelGasMask extends HumanoidModel<LivingEntity> {

    public static final ModelLayerLocation LAYER = new ModelLayerLocation(NuclearTechMod.withDefaultNamespace("gas_mask"), "main");

    public ModelGasMask(ModelPart root) {
        super(root);
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

        mask.addOrReplaceChild("shape1", CubeListBuilder.create().texOffs(0, 0).addBox(0F, 0F, 0F, 8, 8, 3),
                PartPose.offsetAndRotation(0F - 4, 0F - 8 + 0.075F / 2, 0F - 4, 0F, 0F, 0F));
        mask.addOrReplaceChild("shape2", CubeListBuilder.create().texOffs(22, 0).addBox(0F, 0F, 0F, 2, 2, 1),
                PartPose.offsetAndRotation(1F - 4, 3F - 8 + 0.075F / 2, -0.5333334F - 4, 0F, 0F, 0F));
        mask.addOrReplaceChild("shape3", CubeListBuilder.create().texOffs(22, 0).addBox(0F, 0F, 0F, 2, 2, 1),
                PartPose.offsetAndRotation(5F - 4, 3F - 8 + 0.075F / 2, -0.5F - 4, 0F, 0F, 0F));
        mask.addOrReplaceChild("shape4", CubeListBuilder.create().texOffs(0, 11).addBox(0F, 0F, 0F, 2, 2, 2),
                PartPose.offsetAndRotation(3F - 4, 5F - 8 + 0.075F / 2, 0F - 4, -0.7853982F, 0F, 0F));
        mask.addOrReplaceChild("shape5", CubeListBuilder.create().texOffs(0, 15).addBox(0F, 2F, -0.5F, 3, 4, 3),
                PartPose.offsetAndRotation(2.5F - 4, 5F - 8 + 0.075F / 2, 0F - 4, -0.7853982F, 0F, 0F));
        mask.addOrReplaceChild("shape6", CubeListBuilder.create().texOffs(0, 22).addBox(0F, 0F, 0F, 8, 1, 5),
                PartPose.offsetAndRotation(0F - 4, 3F - 8 + 0.075F / 2, 3F - 4, 0F, 0F, 0F));

        return LayerDefinition.create(mesh, 64, 32);
    }

    // Original ModelGasMask.render: only the mask is drawn, scaled about the model origin
    @Override
    public void renderToBuffer(PoseStack poseStack, VertexConsumer buffer, int packedLight, int packedOverlay, int color) {
        poseStack.pushPose();

        if(this.young) {
            float f6 = 2.0F;
            poseStack.scale(1.5F / f6, 1.5F / f6, 1.5F / f6);
            poseStack.translate(0.0F, 16.0F / 16.0F, 0.0F);
        } else {
            poseStack.scale(1.15F, 1.15F, 1.15F);
        }

        this.head.render(poseStack, buffer, packedLight, packedOverlay, color);
        poseStack.popPose();
    }
}
