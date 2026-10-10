package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.oil.MachineCokerBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.mojang.blaze3d.systems.RenderSystem;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

public class RenderCoker extends BlockEntityRendererNT<MachineCokerBlockEntity> implements IBEWLRProvider {

    @Override public BlockEntityRenderer<MachineCokerBlockEntity> create(Context context) { return new RenderCoker(); }

    @Override
    public void render(MachineCokerBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        // The original tower is axis-aligned and does not rotate with placement facing.
        RenderContext.translate(0.5F, 0F, 0.5F);
        this.renderModel();
    }

    private void renderModel() {
        RenderSystem.disableCull();
        try {
            bindTexture(ResourceManager.coker_tex);
            ResourceManager.coker.renderAll();
        } finally { RenderSystem.enableCull(); }
    }

    @Override public AABB getRenderBoundingBox(MachineCokerBlockEntity be) { return be.getRenderBoundingBox(); }
    @Override public Item getItemForRenderer() { return NtmBlocks.MACHINE_COKER.asItem(); }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -5F, 0F);
                RenderContext.scale(2.75F, 2.75F, 2.75F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.scale(0.25F, 0.25F, 0.25F);
                RenderCoker.this.renderModel();
            }
        };
    }
}
