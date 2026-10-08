package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.boiler.MachineIndustrialBoilerBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.client.renderer.blockentity.BlockEntityRendererProvider.Context;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

public class RenderIndustrialBoiler extends BlockEntityRendererNT<MachineIndustrialBoilerBlockEntity> implements IBEWLRProvider {

    @Override
    public BlockEntityRenderer<MachineIndustrialBoilerBlockEntity> create(Context context) {
        return new RenderIndustrialBoiler();
    }

    @Override
    public void render(MachineIndustrialBoilerBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        // As the original RenderIndustrialBoiler: centred only, without a facing rotation or a pulse when the steam
        // tank is nearly full; the original renders the same orientation for every facing.
        RenderContext.translate(0.5F, 0.0F, 0.5F);

        bindTexture(ResourceManager.INDUSTRIAL_BOILER_TEX);
        ResourceManager.industrial_boiler.renderAll();
    }

    @Override
    public Item getItemForRenderer() {
        return NtmBlocks.MACHINE_INDUSTRIAL_BOILER.asItem();
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -3F, 0F);
                RenderContext.scale(2.5F, 2.5F, 2.5F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
                bindTexture(ResourceManager.INDUSTRIAL_BOILER_TEX);
                ResourceManager.industrial_boiler.renderAll();
            }
        };
    }
}
