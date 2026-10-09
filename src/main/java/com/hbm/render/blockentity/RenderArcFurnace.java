package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.MachineArcFurnaceBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.FullBright;
import com.hbm.render.util.RenderContext;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

/** Original RenderArcFurnace. The liquid contents (ContentsHot) belong to the liquid mode, which is not ported (Goal 13B B1). */
public class RenderArcFurnace extends BlockEntityRendererNT<MachineArcFurnaceBlockEntity> implements IBEWLRProvider {

    // electrode states of the block entity: 0 none, 1 fresh, 2 used, 3 depleted
    private static final int NONE = 0;
    private static final int FRESH = 1;
    private static final int USED = 2;
    private static final int DEPLETED = 3;

    @Override
    public BlockEntityRenderer<MachineArcFurnaceBlockEntity> create(Context context) {
        return new RenderArcFurnace();
    }

    @Override
    public void render(MachineArcFurnaceBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        Direction facing = be.getBlockState().getValue(DummyableBlock.FACING);

        RenderContext.translate(0.5F, 0F, 0.5F);
        // Original RenderArcFurnace meta table: 2 (north) 90, 4 (west) 180, 3 (south) 270, 5 (east) 0
        switch(facing) {
            case NORTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            case SOUTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(270F));
            case WEST -> RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            case EAST -> RenderContext.mulPose(Axis.YP.rotationDegrees(0F));
            default -> { }
        }

        float lift = be.prevLid + (be.lid - be.prevLid) * partialTicks;
        double time = be.getLevel().getGameTime() + partialTicks;
        byte[] electrodes = be.electrodeStates;

        bindTexture(ResourceManager.ARC_FURNACE_TEX);
        ResourceManager.arc_furnace.renderPart("Furnace");

        if(be.hasMaterial) ResourceManager.arc_furnace.renderPart("ContentsCold");

        RenderContext.translate(0F, 2F * lift, 0F);
        if(be.isProgressing) RenderContext.translate(0F, 0F, (float) (Math.sin(time) * 0.005));
        ResourceManager.arc_furnace.renderPart("Lid");
        for(int i = 0; i < 3; i++) if(electrodes[i] != NONE) ResourceManager.arc_furnace.renderPart("Ring" + (i + 1));
        for(int i = 0; i < 3; i++) if(electrodes[i] == FRESH) ResourceManager.arc_furnace.renderPart("Electrode" + (i + 1));

        // used and depleted electrodes glow
        RenderContext.setLightning(false);
        RenderSystem.disableCull();
        FullBright.enable();
        for(int i = 0; i < 3; i++) if(electrodes[i] == USED) ResourceManager.arc_furnace.renderPart("Electrode" + (i + 1) + "Hot");
        for(int i = 0; i < 3; i++) if(electrodes[i] == DEPLETED) ResourceManager.arc_furnace.renderPart("Electrode" + (i + 1) + "Short");
        FullBright.disable();
        RenderSystem.enableCull();
        RenderContext.setLightning(true);

        // the cables pivot around the lid at y = 5.5, cable 1 and 3 are offset by half a block along z
        float[] pivotZ = { 0.5F, 0F, -0.5F };
        for(int i = 0; i < 3; i++) {
            if(electrodes[i] == NONE) continue;
            RenderContext.pushPose();
            RenderContext.translate(0F, 5.5F, pivotZ[i]);
            if(be.isProgressing) RenderContext.mulPose(Axis.XP.rotationDegrees((float) (Math.sin(time / 2) * 30)));
            RenderContext.translate(0F, -5.5F, -pivotZ[i]);
            ResourceManager.arc_furnace.renderPart("Cable" + (i + 1));
            RenderContext.popPose();
        }
    }

    @Override
    public AABB getRenderBoundingBox(MachineArcFurnaceBlockEntity be) {
        // original (-3, 0, -3) to (+4, +6, +4) around the core, as corner coordinates
        BlockPos pos = be.getBlockPos();
        return new AABB(pos.getX() - 3, pos.getY(), pos.getZ() - 3, pos.getX() + 4, pos.getY() + 6, pos.getZ() + 4);
    }

    @Override
    public Item getItemForRenderer() {
        return NtmBlocks.MACHINE_ARC_FURNACE.asItem();
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -3F, 0F);
                RenderContext.scale(3.5F, 3.5F, 3.5F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.scale(0.5F, 0.5F, 0.5F);
                bindTexture(ResourceManager.ARC_FURNACE_TEX);
                for(String part : new String[] { "Furnace", "Lid", "Ring1", "Ring2", "Ring3", "Electrode1", "Electrode2", "Electrode3", "Cable1", "Cable2", "Cable3" }) {
                    ResourceManager.arc_furnace.renderPart(part);
                }
            }
        };
    }
}
