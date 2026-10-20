package com.hbm.render.model;

import com.hbm.render.loader.HFRWavefrontObject;
import com.mojang.math.Transformation;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.block.model.BakedQuad;
import net.minecraft.client.renderer.block.model.ItemTransforms;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.core.Direction;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.client.ChunkRenderTypeSet;
import net.neoforged.neoforge.client.model.QuadTransformers;
import net.neoforged.neoforge.client.model.data.ModelData;
import org.joml.Matrix4f;
import org.joml.Vector3f;

import javax.annotation.Nullable;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

/**
 * The RBMK fuel channel body (original RenderRBMKRod, an ISBRH). In the level (:59-82) every block of the column draws the four
 * vertical faces of the full cube with the side texture (renderStandardBlock with overrideOnlyRenderSides), each culled like a
 * block face, and the OBJ parts "Cap" (top texture) and "Inner" of rbmk_element.obj. As an item (:21-56) it draws four such
 * segments scaled 0.35 at y -0.675 with the "Rods" of rbmk_element_rods.obj in the variant's fuel texture, tinted 0x304825.
 * The rods in a placed column and the lid are drawn by RenderRBMKRod.
 */
public class RBMKElementBakedModel extends LevelAwareWavefrontBakedModel {

    /** Original renderInventoryBlock: tessellator.setColorOpaque_I(0x304825) for the rods. */
    private static final int ITEM_ROD_COLOR = 0x304825;

    private static final ChunkRenderTypeSet RENDER_TYPE = ChunkRenderTypeSet.of(RenderType.cutout());

    private final TextureAtlasSprite side;

    private final List<BakedQuad> levelQuads;
    private final Map<Direction, List<BakedQuad>> levelSides = new EnumMap<>(Direction.class);
    private final List<BakedQuad> itemQuads;

    public RBMKElementBakedModel(HFRWavefrontObject element, HFRWavefrontObject rods, TextureAtlasSprite side, TextureAtlasSprite top, TextureAtlasSprite inner, TextureAtlasSprite fuel, ItemTransforms transforms) {
        super(element, transforms);
        this.side = side;

        // Placed: OBJ space is centred on the block in x and z, like SimpleWavefrontBakedModel.
        Matrix4f level = new Matrix4f().translate(0.5F, 0.0F, 0.5F);
        List<BakedQuad> quads = new ArrayList<>();
        quads.addAll(bakeSimpleQuads(List.of("Cap"), level, top));
        quads.addAll(bakeSimpleQuads(List.of("Inner"), level, inner));
        this.levelQuads = Collections.unmodifiableList(quads);
        for(Direction dir : Direction.Plane.HORIZONTAL) this.levelSides.put(dir, List.of(sideQuad(dir, level, side)));

        // Item: the item model space is 0..1, the original inventory space is centred on the origin.
        RodBaker rodBaker = new RodBaker(rods);
        List<BakedQuad> item = new ArrayList<>();
        for(int i = 0; i < 4; i++) {
            Matrix4f segment = new Matrix4f().translate(0.5F, 0.5F - 0.675F, 0.5F).scale(0.35F).translate(0.0F, i, 0.0F);
            item.addAll(bakeSimpleQuads(List.of("Inner"), segment, inner));
            item.addAll(bakeSimpleQuads(List.of("Cap"), segment, top));
            for(Direction dir : Direction.Plane.HORIZONTAL) item.add(sideQuad(dir, segment, side));
            for(BakedQuad quad : rodBaker.bake(segment, fuel)) {
                tint(quad, ITEM_ROD_COLOR);
                item.add(quad);
            }
        }
        this.itemQuads = Collections.unmodifiableList(item);
    }

    @Override
    public List<BakedQuad> getQuads(@Nullable BlockState state, @Nullable Direction direction, RandomSource random, ModelData data, @Nullable RenderType type) {

        if(data.has(IN_LEVEL)) {
            if(direction == null) return levelQuads;
            return levelSides.getOrDefault(direction, Collections.emptyList());
        }

        return direction == null ? itemQuads : Collections.emptyList();
    }

    /**
     * Items are drawn through this three-argument getQuads (ItemRenderer.renderModelLists), which LevelAwareWavefrontBakedModel
     * answers with nothing so that level-only models stay out of item rendering; the fuel channel has an item form, so it answers
     * with the item quads here (Goal 24 acceptance D1b).
     */
    @Override
    public List<BakedQuad> getQuads(@Nullable BlockState state, @Nullable Direction direction, RandomSource random) {
        return direction == null ? itemQuads : Collections.emptyList();
    }

    /**
     * One vertical face of the cube -0.5..0.5 / 0..1 / -0.5..0.5 (the inventory layout), vertex order and UVs as vanilla FaceBakery,
     * then moved by the given matrix. Its cull face is its direction, as for a standard block side.
     */
    private static BakedQuad sideQuad(Direction dir, Matrix4f matrix, TextureAtlasSprite sprite) {
        float[][] corners = switch(dir) {
            case NORTH -> new float[][] {{0.5F, 1, -0.5F}, {0.5F, 0, -0.5F}, {-0.5F, 0, -0.5F}, {-0.5F, 1, -0.5F}};
            case SOUTH -> new float[][] {{-0.5F, 1, 0.5F}, {-0.5F, 0, 0.5F}, {0.5F, 0, 0.5F}, {0.5F, 1, 0.5F}};
            case WEST -> new float[][] {{-0.5F, 1, -0.5F}, {-0.5F, 0, -0.5F}, {-0.5F, 0, 0.5F}, {-0.5F, 1, 0.5F}};
            default -> new float[][] {{0.5F, 1, 0.5F}, {0.5F, 0, 0.5F}, {0.5F, 0, -0.5F}, {0.5F, 1, -0.5F}};
        };
        float[][] uvs = {{0, 0}, {0, 1}, {1, 1}, {1, 0}};
        Vector3f normal = new Vector3f(dir.getStepX(), dir.getStepY(), dir.getStepZ());

        int[] vertexData = new int[32];
        for(int i = 0; i < 4; i++) GeometryBakeUtil.putVertex(vertexData, i, corners[i][0], corners[i][1], corners[i][2], uvs[i][0], uvs[i][1], normal, sprite);

        List<BakedQuad> quad = new ArrayList<>(List.of(new BakedQuad(vertexData, -1, dir, sprite, true, true)));
        QuadTransformers.applying(new Transformation(matrix)).processInPlace(quad);
        return quad.get(0);
    }

    /** Writes an opaque RGB colour into the vertex colour of every vertex (BLOCK format: bytes R, G, B, A). */
    private static void tint(BakedQuad quad, int rgb) {
        int[] vertices = quad.getVertices();
        int abgr = 0xFF000000 | ((rgb & 0xFF) << 16) | (rgb & 0xFF00) | ((rgb >> 16) & 0xFF);
        for(int i = 0; i < 4; i++) vertices[i * 8 + 3] = abgr;
    }

    // Bakes parts of the second OBJ (rbmk_element_rods.obj) with the same geometry code.
    private static class RodBaker extends AbstractWavefrontBakedModel {

        RodBaker(HFRWavefrontObject model) {
            super(model, ItemTransforms.NO_TRANSFORMS);
        }

        List<BakedQuad> bake(Matrix4f matrix, TextureAtlasSprite sprite) {
            return bakeSimpleQuads(List.of("Rods"), matrix, sprite);
        }

        @Override public List<BakedQuad> getQuads(@Nullable BlockState state, @Nullable Direction direction, RandomSource random) { return Collections.emptyList(); }
        @Override public TextureAtlasSprite getParticleIcon() { return null; }
    }

    @Override public ChunkRenderTypeSet getRenderTypes(BlockState state, RandomSource rand, ModelData data) { return RENDER_TYPE; }

    @Override
    public TextureAtlasSprite getParticleIcon() {
        return side;
    }
}
