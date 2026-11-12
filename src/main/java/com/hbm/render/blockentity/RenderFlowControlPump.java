package com.hbm.render.blockentity;

import com.hbm.blockentity.network.FlowControlPumpBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
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

/** Flow control pump: the body, the rails above and below where a block is, and the spinning rotor (original RenderFlowControlPump.java:16-72). */
public class RenderFlowControlPump extends BlockEntityRendererNT<FlowControlPumpBlockEntity> implements IBEWLRProvider {

    @Override public BlockEntityRenderer<FlowControlPumpBlockEntity> create(Context context) { return new RenderFlowControlPump(); }

    @Override
    public void render(FlowControlPumpBlockEntity pump, MultiBufferSource buffer, float partialTicks) {
        RenderContext.translate(0.5F, 0F, 0.5F);

        switch(pump.getBlockState().getValue(DummyableBlock.FACING)) {
            case NORTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            case WEST -> RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            case SOUTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(270F));
            default -> { }
        }

        bindTexture(ResourceManager.FLOW_CONTROL_PUMP_TEX);
        ResourceManager.flow_control_pump.renderPart("Pump");
        if(pump.topRail) ResourceManager.flow_control_pump.renderPart("RailTop");
        if(pump.bottomRail) ResourceManager.flow_control_pump.renderPart("RailBottom");

        float rotor = pump.prevRotor + (pump.rotor - pump.prevRotor) * partialTicks;

        RenderContext.translate(0F, 0.5F, 0F);
        RenderContext.mulPose(Axis.ZN.rotationDegrees(rotor));
        RenderContext.translate(0F, -0.5F, 0F);
        ResourceManager.flow_control_pump.renderPart("Rotor");
    }

    // FlowControlPump.java:283-289: one block around the core
    @Override public AABB getRenderBoundingBox(FlowControlPumpBlockEntity be) { return new AABB(be.getBlockPos()).inflate(1, 0, 1); }

    @Override
    public Item[] getItemsForRenderer() {
        return new Item[] {NtmBlocks.FLOW_CONTROL_PUMP.asItem()};
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.scale(5F, 5F, 5F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                bindTexture(ResourceManager.FLOW_CONTROL_PUMP_TEX);
                ResourceManager.flow_control_pump.renderPart("Pump");
                ResourceManager.flow_control_pump.renderPart("Rotor");
                ResourceManager.flow_control_pump.renderPart("RailBottom");
            }
        };
    }
}
