package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.oil.MachineFractionTowerBlockEntity;
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

public class RenderFractionTower extends BlockEntityRendererNT<MachineFractionTowerBlockEntity> implements IBEWLRProvider {

    @Override public BlockEntityRenderer<MachineFractionTowerBlockEntity> create(Context context) { return new RenderFractionTower(); }

    @Override
    public void render(MachineFractionTowerBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        // The original tower is axis-aligned and does not rotate with placement facing.
        RenderContext.translate(0.5F, 0F, 0.5F);
        RenderSystem.disableCull();
        bindTexture(ResourceManager.fraction_tower_tex);
        ResourceManager.fraction_tower.renderAll();
        RenderSystem.enableCull();
    }

    @Override public AABB getRenderBoundingBox(MachineFractionTowerBlockEntity be) { return be.getRenderBoundingBox(); }
    @Override public Item getItemForRenderer() { return NtmBlocks.MACHINE_FRACTION_TOWER.asItem(); }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -2.5F, 0F);
                RenderContext.scale(3.25F, 3.25F, 3.25F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                bindTexture(ResourceManager.fraction_tower_tex);
                ResourceManager.fraction_tower.renderAll();
            }
        };
    }
}
