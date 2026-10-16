package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.MachineGasCentrifugeBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.LevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.core.Direction;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

/**
 * The gas centrifuge branch of the original RenderCentrifuge (:39-44, :76-77). Kept as its own renderer because the
 * IBEWLRProvider loop in ClientProxy registers the item renderer once per block entity renderer, so a shared class
 * registered for both block entity types would register both items twice.
 */
public class RenderGasCentrifuge extends BlockEntityRendererNT<MachineGasCentrifugeBlockEntity> implements IBEWLRProvider {

    @Override
    public BlockEntityRenderer<MachineGasCentrifugeBlockEntity> create(Context context) {
        return new RenderGasCentrifuge();
    }

    @Override
    public void render(MachineGasCentrifugeBlockEntity be, MultiBufferSource buffer, float partialTicks) {

        RenderContext.translate(0.5F, 0.0F, 0.5F);

        // Original RenderCentrifuge.java:26-31 angles for the placement direction (NEO FACING points the same way as the original
        // dir): NORTH 90, WEST 180, SOUTH 270, EAST 0, like RenderArcWelder; NEO's RenderCentrifuge keeps its own older mapping.
        Direction facing = be.getBlockState().getValue(DummyableBlock.FACING);
        switch(facing) {
            case NORTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            case SOUTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(270F));
            case WEST -> RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            case EAST -> RenderContext.mulPose(Axis.YP.rotationDegrees(0F));
        }
        // The gas centrifuge model faces the other way (original RenderCentrifuge.java:41).
        RenderContext.mulPose(Axis.YP.rotationDegrees(180F));

        RenderSystem.disableCull();
        bindTexture(ResourceManager.GAS_CENTRIFUGE_TEX);
        ResourceManager.gasCentrifuge.renderPart("Centrifuge");
        ResourceManager.gasCentrifuge.renderPart("Flag");
        RenderSystem.enableCull();
    }

    /** The model is five blocks tall (original getRenderBoundingBox :362-371); wired like RenderChemicalPlant. */
    @Override
    public AABB getRenderBoundingBox(MachineGasCentrifugeBlockEntity be) {
        return be.getRenderBoundingBox();
    }

    @Override
    public int getPacketLight(int packedLight, MachineGasCentrifugeBlockEntity be) {
        if(be.getLevel() != null && be.getBlockState().getBlock() instanceof DummyableBlock dummy) {
            return LevelRenderer.getLightColor(be.getLevel(), be.getBlockPos().above(dummy.getDimensions()[0]));
        }
        return packedLight;
    }

    @Override
    public Item getItemForRenderer() {
        return NtmBlocks.MACHINE_GAS_CENTRIFUGE.asItem();
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0, -4F, 0);
                RenderContext.scale(3.5F, 3.5F, 3.5F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                // The item model omits the flag, as in the original.
                bindTexture(ResourceManager.GAS_CENTRIFUGE_TEX);
                ResourceManager.gasCentrifuge.renderPart("Centrifuge");
            }
        };
    }
}
