package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.oil.MachineCatalyticCrackerBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.core.Direction;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

public class RenderCatalyticCracker extends BlockEntityRendererNT<MachineCatalyticCrackerBlockEntity> implements IBEWLRProvider {

    @Override
    public BlockEntityRenderer<MachineCatalyticCrackerBlockEntity> create(Context context) {
        return new RenderCatalyticCracker();
    }

    @Override
    public void render(MachineCatalyticCrackerBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        Direction facing = be.getBlockState().getValue(DummyableBlock.FACING);

        RenderContext.translate(0.5F, 0F, 0.5F);
        // Original RenderCatalyticCracker meta table: 2 (north) 90, 4 (west) 180, 3 (south) 270, 5 (east) 0
        switch(facing) {
            case NORTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            case SOUTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(270F));
            case WEST -> RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            case EAST -> RenderContext.mulPose(Axis.YP.rotationDegrees(0F));
        }

        RenderSystem.disableCull();
        bindTexture(ResourceManager.CATALYTIC_CRACKER_TEX);
        ResourceManager.catalytic_cracker.renderAll();
        RenderSystem.enableCull();
    }

    @Override
    public AABB getRenderBoundingBox(MachineCatalyticCrackerBlockEntity be) {
        return be.getRenderBoundingBox();
    }

    @Override
    public Item getItemForRenderer() {
        return NtmBlocks.MACHINE_CATALYTIC_CRACKER.asItem();
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -3.5F, 0F);
                RenderContext.scale(1.8F, 1.8F, 1.8F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.scale(0.5F, 0.5F, 0.5F);
                bindTexture(ResourceManager.CATALYTIC_CRACKER_TEX);
                ResourceManager.catalytic_cracker.renderAll();
            }
        };
    }
}
