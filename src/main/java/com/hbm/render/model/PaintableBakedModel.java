package com.hbm.render.model;

import com.hbm.blockentity.network.IPaintableBlockEntity;
import com.hbm.blocks.states.NtmBlockStateProperties;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.block.model.BakedQuad;
import net.minecraft.client.renderer.block.model.BlockElementFace;
import net.minecraft.client.renderer.block.model.BlockFaceUV;
import net.minecraft.client.renderer.block.model.FaceBakery;
import net.minecraft.client.renderer.block.model.ItemTransforms;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.client.resources.model.BakedModel;
import net.minecraft.client.resources.model.BlockModelRotation;
import net.minecraft.core.Direction;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.client.ChunkRenderTypeSet;
import net.neoforged.neoforge.client.model.data.ModelData;
import org.joml.Vector3f;

import javax.annotation.Nullable;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

/**
 * Full-cube model of the paintable cable and duct, standing in for the original two-pass rendering (IBlockMultiPass with
 * BlockCablePaintable.getIcon / FluidDuctPaintable.getIcon). Unpainted: the base texture plus the port overlay, which for the duct is
 * the fluid-coloured overlay (tint index 1). Painted: the paint block's own model, from {@link IPaintableBlockEntity#PAINT}, plus the
 * untinted port overlay unless HIDE_OVERLAY is set. The overlay is drawn in the cutout layer.
 */
public class PaintableBakedModel extends AbstractBakedModel {

    public static final int OVERLAY_TINT = 1;
    private static final ChunkRenderTypeSet CUTOUT = ChunkRenderTypeSet.of(RenderType.cutout());

    private final TextureAtlasSprite base;
    private final Map<Direction, List<BakedQuad>> unpainted = new EnumMap<>(Direction.class);
    private final Map<Direction, List<BakedQuad>> paintedOverlay = new EnumMap<>(Direction.class);

    /**
     * @param overlayUnpainted overlay drawn on the unpainted block, tinted with tint index 1 when {@code tintUnpainted}
     * @param overlayPainted overlay drawn over the paint, never tinted
     */
    public PaintableBakedModel(TextureAtlasSprite base, TextureAtlasSprite overlayUnpainted, boolean tintUnpainted, TextureAtlasSprite overlayPainted) {
        super(true, true, false, true, ItemTransforms.NO_TRANSFORMS);
        this.base = base;
        for(Direction dir : Direction.values()) {
            this.unpainted.put(dir, List.of(face(base, dir, BlockElementFace.NO_TINT), face(overlayUnpainted, dir, tintUnpainted ? OVERLAY_TINT : BlockElementFace.NO_TINT)));
            this.paintedOverlay.put(dir, List.of(face(overlayPainted, dir, BlockElementFace.NO_TINT)));
        }
    }

    private static BakedQuad face(TextureAtlasSprite sprite, Direction dir, int tint) {
        BlockElementFace face = new BlockElementFace(dir, tint, "", new BlockFaceUV(new float[] { 0F, 0F, 16F, 16F }, 0));
        return new FaceBakery().bakeQuad(new Vector3f(0F, 0F, 0F), new Vector3f(16F, 16F, 16F), face, sprite, dir, BlockModelRotation.X0_Y0, null, true);
    }

    @Nullable
    private static BakedModel paintModel(ModelData data) {
        BlockState paint = data.get(IPaintableBlockEntity.PAINT);
        return paint == null ? null : Minecraft.getInstance().getBlockRenderer().getBlockModel(paint);
    }

    @Override
    public List<BakedQuad> getQuads(@Nullable BlockState state, @Nullable Direction side, RandomSource rand) {
        return this.getQuads(state, side, rand, ModelData.EMPTY, null);
    }

    @Override
    public List<BakedQuad> getQuads(@Nullable BlockState state, @Nullable Direction side, RandomSource rand, ModelData data, @Nullable RenderType renderType) {
        boolean cutout = renderType == null || renderType == RenderType.cutout();
        BlockState paint = data.get(IPaintableBlockEntity.PAINT);

        if(paint == null) {
            return side != null && cutout ? this.unpainted.get(side) : List.of();
        }

        BakedModel paintModel = Minecraft.getInstance().getBlockRenderer().getBlockModel(paint);
        List<BakedQuad> quads = new ArrayList<>();
        // A separate random: the renderer seeds rand for this getQuads call, and a weighted paint model picks its variant from it
        if(renderType == null || paintModel.getRenderTypes(paint, RandomSource.create(42L), ModelData.EMPTY).contains(renderType)) {
            quads.addAll(paintModel.getQuads(paint, side, rand, ModelData.EMPTY, renderType));
        }
        boolean hidden = state != null && state.hasProperty(NtmBlockStateProperties.HIDE_OVERLAY) && state.getValue(NtmBlockStateProperties.HIDE_OVERLAY);
        if(side != null && cutout && !hidden) quads.addAll(this.paintedOverlay.get(side));
        return quads;
    }

    @Override
    public ChunkRenderTypeSet getRenderTypes(BlockState state, RandomSource rand, ModelData data) {
        BlockState paint = data.get(IPaintableBlockEntity.PAINT);
        if(paint == null) return CUTOUT;
        BakedModel paintModel = Minecraft.getInstance().getBlockRenderer().getBlockModel(paint);
        return ChunkRenderTypeSet.union(paintModel.getRenderTypes(paint, rand, ModelData.EMPTY), CUTOUT);
    }

    @Override
    public TextureAtlasSprite getParticleIcon(ModelData data) {
        BakedModel paintModel = paintModel(data);
        return paintModel != null ? paintModel.getParticleIcon(ModelData.EMPTY) : this.base;
    }

    @Override
    public TextureAtlasSprite getParticleIcon() {
        return this.base;
    }
}
