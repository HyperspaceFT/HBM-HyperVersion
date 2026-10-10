package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.MachineCombustionEngineBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.fluid.Fluids.CD_Canister;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

public class RenderCombustionEngine extends BlockEntityRendererNT<MachineCombustionEngineBlockEntity> implements IBEWLRProvider {

    @Override
    public BlockEntityRenderer<MachineCombustionEngineBlockEntity> create(Context context) {
        return new RenderCombustionEngine();
    }

    @Override
    public void render(MachineCombustionEngineBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        RenderContext.translate(0.5F, 0F, 0.5F);
        switch(be.getBlockState().getValue(DummyableBlock.FACING)) {
            case NORTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            case EAST -> RenderContext.mulPose(Axis.YP.rotationDegrees(0F));
            case SOUTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(270F));
            case WEST -> RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            default -> { }
        }
        RenderContext.translate(-0.5F, 0F, 3F);
        this.bindTexture(ResourceManager.combustion_engine_tex);
        ResourceManager.combustion_engine.renderPart("Engine");

        CD_Canister canister = be.tank.getTankType().getContainer(CD_Canister.class);
        if(canister != null) {
            int color = canister.color;
            // Retain the original canister tint's 256 divisor rather than changing its brightness.
            RenderContext.setColor(((color >> 16) & 255) / 256F, ((color >> 8) & 255) / 256F, (color & 255) / 256F, 1F);
        }
        try {
            ResourceManager.combustion_engine.renderPart("Canister");
        } finally {
            RenderContext.setColor(1F, 1F, 1F, 1F);
        }

        RenderContext.pushPose();
        RenderContext.translate(1F, 0F, -2.6875F);
        RenderContext.mulPose(Axis.YN.rotationDegrees(be.prevDoorAngle + (be.doorAngle - be.prevDoorAngle) * partialTicks));
        RenderContext.translate(-1F, 0F, 2.6875F);
        ResourceManager.combustion_engine.renderPart("Hatch");
        RenderContext.popPose();
    }

    @Override
    public AABB getRenderBoundingBox(MachineCombustionEngineBlockEntity be) {
        return be.getRenderBoundingBox();
    }

    @Override
    public Item getItemForRenderer() { return NtmBlocks.MACHINE_COMBUSTION_ENGINE.asItem(); }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -1F, 0F);
                RenderContext.scale(2.75F, 2.75F, 2.75F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
                RenderContext.translate(0F, 0F, 2.75F);
                RenderCombustionEngine.this.bindTexture(ResourceManager.combustion_engine_tex);
                ResourceManager.combustion_engine.renderAll();
            }
        };
    }
}
