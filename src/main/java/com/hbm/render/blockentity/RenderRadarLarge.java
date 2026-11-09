package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.MachineRadarLargeBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.util.Mth;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

/** Original RenderRadarLarge.java:16-57. The model does not turn with the facing; only the dish spins. */
public class RenderRadarLarge extends BlockEntityRendererNT<MachineRadarLargeBlockEntity> implements IBEWLRProvider {

    @Override public BlockEntityRenderer<MachineRadarLargeBlockEntity> create(Context context) { return new RenderRadarLarge(); }

    @Override
    public void render(MachineRadarLargeBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        RenderContext.translate(0.5F, 0F, 0.5F);
        RenderContext.mulPose(Axis.YP.rotationDegrees(180F));

        RenderSystem.disableCull();
        bindTexture(ResourceManager.RADAR_LARGE_TEX);
        ResourceManager.radar_large.renderPart("Radar");

        RenderContext.mulPose(Axis.YN.rotationDegrees(Mth.lerp(partialTicks, be.prevRotation, be.rotation)));
        ResourceManager.radar_large.renderPart("Dish");
        RenderSystem.enableCull();
    }

    /** Original TileEntityMachineRadarLarge.java:40-55, around the core; computed per block entity. */
    @Override
    public AABB getRenderBoundingBox(MachineRadarLargeBlockEntity be) {
        int x = be.getBlockPos().getX();
        int y = be.getBlockPos().getY();
        int z = be.getBlockPos().getZ();
        return new AABB(x - 5, y, z - 5, x + 6, y + 10, z + 6);
    }

    @Override
    public Item getItemForRenderer() {
        return NtmBlocks.MACHINE_RADAR_LARGE.asItem();
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -5F, 0F);
                RenderContext.scale(3F, 3F, 3F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                RenderSystem.disableCull();
                RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
                RenderContext.scale(0.5F, 0.5F, 0.5F);
                bindTexture(ResourceManager.RADAR_LARGE_TEX);
                ResourceManager.radar_large.renderPart("Radar");
                RenderContext.mulPose(Axis.YN.rotationDegrees((System.currentTimeMillis() % 3600) * 0.1F));
                ResourceManager.radar_large.renderPart("Dish");
                RenderSystem.enableCull();
            }
        };
    }
}
