package com.hbm.render.blockentity;

import com.hbm.blockentity.network.PylonMediumBlockEntity;
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
import net.minecraft.world.level.block.state.BlockState;

/** Medium pylons, with or without a transformer (original RenderPylonMedium.java:16-91). */
public class RenderPylonMedium extends RenderPylonBase<PylonMediumBlockEntity> implements IBEWLRProvider {

    @Override public BlockEntityRenderer<PylonMediumBlockEntity> create(Context context) { return new RenderPylonMedium(); }

    @Override
    public void render(PylonMediumBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        RenderContext.pushPose();
        RenderContext.translate(0.5F, 0F, 0.5F);

        switch(be.getFacing()) {
            case NORTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            case WEST -> RenderContext.mulPose(Axis.YP.rotationDegrees(270F));
            case EAST -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            default -> { }
        }

        BlockState state = be.getBlockState();
        boolean steel = state.is(NtmBlocks.RED_PYLON_MEDIUM_STEEL.get()) || state.is(NtmBlocks.RED_PYLON_MEDIUM_STEEL_TRANSFORMER.get());
        bindTexture(steel ? ResourceManager.PYLON_MEDIUM_STEEL_TEX : ResourceManager.PYLON_MEDIUM_TEX);

        ResourceManager.pylon_medium.renderPart("Pylon");
        if(be.hasTransformer()) ResourceManager.pylon_medium.renderPart("Transformer");

        RenderContext.popPose();

        this.renderLinesGeneric(be, buffer);
    }

    @Override
    public Item[] getItemsForRenderer() {
        return new Item[] {
                NtmBlocks.RED_PYLON_MEDIUM_WOOD.asItem(),
                NtmBlocks.RED_PYLON_MEDIUM_WOOD_TRANSFORMER.asItem(),
                NtmBlocks.RED_PYLON_MEDIUM_STEEL.asItem(),
                NtmBlocks.RED_PYLON_MEDIUM_STEEL_TRANSFORMER.asItem()
        };
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(1F, -5F, 0F);
                RenderContext.scale(4.5F, 4.5F, 4.5F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
                RenderContext.scale(0.5F, 0.5F, 0.5F);
                RenderContext.translate(0.75F, 0F, 0F);

                boolean steel = stack.is(NtmBlocks.RED_PYLON_MEDIUM_STEEL.asItem()) || stack.is(NtmBlocks.RED_PYLON_MEDIUM_STEEL_TRANSFORMER.asItem());
                bindTexture(steel ? ResourceManager.PYLON_MEDIUM_STEEL_TEX : ResourceManager.PYLON_MEDIUM_TEX);
                ResourceManager.pylon_medium.renderPart("Pylon");

                if(stack.is(NtmBlocks.RED_PYLON_MEDIUM_WOOD_TRANSFORMER.asItem()) || stack.is(NtmBlocks.RED_PYLON_MEDIUM_STEEL_TRANSFORMER.asItem()))
                    ResourceManager.pylon_medium.renderPart("Transformer");
            }
        };
    }
}
