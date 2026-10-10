package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.MachineDieselBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.MachineDieselBlock;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.core.Direction;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

public class RenderDieselGen extends BlockEntityRendererNT<MachineDieselBlockEntity> implements IBEWLRProvider {

    @Override
    public BlockEntityRenderer<MachineDieselBlockEntity> create(Context context) {
        return new RenderDieselGen();
    }

    @Override
    public void render(MachineDieselBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        Direction facing = be.getBlockState().getValue(MachineDieselBlock.FACING);

        RenderContext.translate(0.5F, 0F, 0.5F);
        // Match the original diesel block's placement metadata to its model rotation.
        switch(facing) {
            case NORTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            case EAST -> RenderContext.mulPose(Axis.YP.rotationDegrees(0F));
            case SOUTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(270F));
            case WEST -> RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            default -> { }
        }

        this.bindTexture(ResourceManager.diesel_tex);
        ResourceManager.diesel.renderPart("Generator");

        if(be.isOn && be.hasAcceptableFuel() && be.tank.getFill() > 0) {
            float swingSide = (float) (Math.sin(System.currentTimeMillis() / 50D) * 0.005D);
            float swingFront = (float) (Math.sin(System.currentTimeMillis() / 25D) * 0.005D);
            RenderContext.translate(swingFront, 0F, swingSide);
        }

        ResourceManager.diesel.renderPart("Engine");
    }

    @Override
    public Item getItemForRenderer() {
        return NtmBlocks.MACHINE_DIESEL.asItem();
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
                RenderContext.scale(2F, 2F, 2F);
                RenderDieselGen.this.bindTexture(ResourceManager.diesel_tex);
                ResourceManager.diesel.renderAll();
            }
        };
    }
}
