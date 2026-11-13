package com.hbm.render.entity.item;

import com.hbm.entity.item.MovingItem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.ItemRenderer;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.client.renderer.texture.TextureAtlas;
import net.minecraft.client.resources.model.BakedModel;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;

import java.util.Random;

/**
 * Original RenderMovingItem.java:21-51: the stack drawn like a dropped item without bobbing or spinning, flat items laid
 * down on the belt, with a tiny per-entity height offset so neighbouring items do not flicker into each other. The
 * offsets differ from the original's (it moved flat items by -0.1875 and turned them in fast graphics) because the 1.21
 * ground transform is not the 1.7.10 one: flat items are centred on the entity and lifted by 0.01 above the belt surface.
 */
public class RenderMovingItem extends EntityRenderer<MovingItem> {

    private final ItemRenderer itemRenderer;

    public RenderMovingItem(EntityRendererProvider.Context context) {
        super(context);
        this.itemRenderer = context.getItemRenderer();
        this.shadowRadius = 0.0F;
    }

    @Override
    public void render(MovingItem entity, float entityYaw, float partialTick, PoseStack poseStack, MultiBufferSource buffer, int packedLight) {

        ItemStack stack = entity.getItemStack();
        if(stack.isEmpty()) return;

        poseStack.pushPose();

        Random rand = new Random(entity.getId());
        poseStack.translate(0, 0.01 + rand.nextDouble() * 0.0625, 0);

        BakedModel model = this.itemRenderer.getModel(stack, entity.level(), null, entity.getId());

        if(!model.isGui3d()) {
            poseStack.mulPose(Axis.XP.rotationDegrees(90F));
            poseStack.translate(0.0, -0.125, 0.0);
        }

        this.itemRenderer.render(stack, ItemDisplayContext.GROUND, false, poseStack, buffer, packedLight, OverlayTexture.NO_OVERLAY, model);

        poseStack.popPose();
        super.render(entity, entityYaw, partialTick, poseStack, buffer, packedLight);
    }

    @Override
    public ResourceLocation getTextureLocation(MovingItem entity) {
        return TextureAtlas.LOCATION_BLOCKS;
    }
}
