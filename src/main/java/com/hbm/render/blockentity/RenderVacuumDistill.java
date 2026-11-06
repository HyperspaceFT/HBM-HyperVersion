package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.oil.MachineVacuumDistillBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

public class RenderVacuumDistill extends BlockEntityRendererNT<MachineVacuumDistillBlockEntity> implements IBEWLRProvider {

    @Override
    public BlockEntityRenderer<MachineVacuumDistillBlockEntity> create(Context context) {
        return new RenderVacuumDistill();
    }

    @Override
    public void render(MachineVacuumDistillBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        RenderContext.translate(0.5F, 0F, 0.5F);
        bindTexture(ResourceManager.VACUUM_DISTILL_TEX);
        ResourceManager.vacuum_distill.renderAll();
    }

    @Override
    public AABB getRenderBoundingBox(MachineVacuumDistillBlockEntity be) {
        return be.getRenderBoundingBox();
    }

    @Override
    public Item getItemForRenderer() {
        return NtmBlocks.MACHINE_VACUUM_DISTILL.asItem();
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -4F, 0F);
                RenderContext.scale(3F, 3F, 3F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.scale(0.5F, 0.5F, 0.5F);
                bindTexture(ResourceManager.VACUUM_DISTILL_TEX);
                ResourceManager.vacuum_distill.renderAll();
            }
        };
    }
}
