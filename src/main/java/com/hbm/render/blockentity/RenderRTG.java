package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.MachineRTGBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.lib.Library;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;

public class RenderRTG extends BlockEntityRendererNT<MachineRTGBlockEntity> implements IBEWLRProvider {

    @Override
    public BlockEntityRenderer<MachineRTGBlockEntity> create(Context context) {
        return new RenderRTG();
    }

    @Override
    public void render(MachineRTGBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        // Original RenderRTG.java:20-55: the generator body, then one connector per side that a cable or machine connects to.
        RenderContext.translate(0.5F, 0F, 0.5F);
        RenderContext.mulPose(Axis.YP.rotationDegrees(180F));

        this.bindTexture(ResourceManager.RTG_TEX);
        ResourceManager.rtg.renderPart("Gen");

        Level level = be.getLevel();
        if(level == null) return;
        BlockPos pos = be.getBlockPos();

        if(Library.canConnect(level, pos.east(), Direction.EAST)) ResourceManager.rtg.renderPart("Connector");

        if(Library.canConnect(level, pos.west(), Direction.WEST)) {
            RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            ResourceManager.rtg.renderPart("Connector");
            RenderContext.mulPose(Axis.YP.rotationDegrees(-180F));
        }

        if(Library.canConnect(level, pos.north(), Direction.NORTH)) {
            RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            ResourceManager.rtg.renderPart("Connector");
            RenderContext.mulPose(Axis.YP.rotationDegrees(-90F));
        }

        if(Library.canConnect(level, pos.south(), Direction.SOUTH)) {
            RenderContext.mulPose(Axis.YP.rotationDegrees(-90F));
            ResourceManager.rtg.renderPart("Connector");
            RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
        }
    }

    @Override
    public Item getItemForRenderer() {
        return NtmBlocks.MACHINE_RTG.asItem();
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -2.5F, 0F);
                RenderContext.scale(5F, 5F, 5F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                // The original item renderer (RenderRTGBlock) draws only the generator body.
                RenderContext.scale(2F, 2F, 2F);
                RenderRTG.this.bindTexture(ResourceManager.RTG_TEX);
                ResourceManager.rtg.renderPart("Gen");
            }
        };
    }
}
