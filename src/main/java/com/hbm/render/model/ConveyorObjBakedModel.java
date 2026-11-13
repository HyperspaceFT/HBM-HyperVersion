package com.hbm.render.model;

import com.hbm.blocks.DummyableBlock;
import com.hbm.render.loader.HFRWavefrontObject;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.block.model.BakedQuad;
import net.minecraft.client.renderer.block.model.ItemTransforms;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.core.Direction;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.Property;
import net.neoforged.neoforge.client.ChunkRenderTypeSet;
import net.neoforged.neoforge.client.model.data.ModelData;
import org.joml.Matrix4f;

import javax.annotation.Nullable;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * The static OBJ shapes of the conveyor splitter (original RenderSplitter) and the acidizer input partitioner (RenderPartitioner),
 * baked into the chunk instead of drawn every frame. Each OBJ group gets its own texture. The original turns the shape by the block's
 * metadata (RenderSplitter.java:49-52, RenderPartitioner.java:45-49); NEO's geometry loader ignores blockstate rotations, so the
 * quads are rotated here by the facing, cached per facing and half. The splitter's two blocks draw the two halves of one shape with
 * their own textures: the core (the original's left block, meta 12 and up) and the second block.
 */
public class ConveyorObjBakedModel extends LevelAwareWavefrontBakedModel {

    /** The partitioner's and the splitter's back textures are partly transparent; the 1.7.10 world pass alpha-tests them. */
    private static final ChunkRenderTypeSet RENDER_TYPE = ChunkRenderTypeSet.of(RenderType.cutout());

    /** OBJ group to sprite, for the core (or the only block) and for the splitter's second block (null when there is none). */
    private final Map<String, TextureAtlasSprite> coreParts;
    @Nullable private final Map<String, TextureAtlasSprite> secondParts;
    private final TextureAtlasSprite particle;
    private final Property<Direction> facing;

    private final List<BakedQuad>[] cache = new List[8];
    private List<BakedQuad> itemQuads;

    public ConveyorObjBakedModel(HFRWavefrontObject model, Map<String, TextureAtlasSprite> coreParts, @Nullable Map<String, TextureAtlasSprite> secondParts, TextureAtlasSprite particle, ItemTransforms transforms) {
        super(model, transforms);
        this.coreParts = coreParts;
        this.secondParts = secondParts;
        this.particle = particle;
        this.facing = secondParts != null ? DummyableBlock.FACING : BlockStateProperties.HORIZONTAL_FACING;
    }

    /**
     * The original's angle by facing, for the splitter's core and the partitioner: north 90, south 270, west 180, east 0 degrees
     * about Y, the OBJ centred on the block's x and z. The splitter's second block takes the core's angle (RenderSplitter.java:48-52
     * gives the core's and the dummy's metadata the same rotation); its own facing points from the core to it, so it is turned
     * clockwise back to the core's first, as CraneSplitterBlock.getTravelDirection does.
     */
    public static float angle(Direction dir) {
        return switch(dir) {
            case NORTH -> 90F;
            case SOUTH -> 270F;
            case WEST -> 180F;
            default -> 0F;
        };
    }

    @Override
    public List<BakedQuad> getQuads(@Nullable BlockState state, @Nullable Direction direction, RandomSource random, ModelData data, @Nullable RenderType type) {
        if(direction != null) return Collections.emptyList();
        if(!data.has(IN_LEVEL)) return this.itemQuads();

        Direction dir = Direction.EAST;
        boolean second = false;

        if(state != null && state.hasProperty(this.facing)) {
            dir = state.getValue(this.facing);
            if(dir.getAxis() == Direction.Axis.Y) dir = Direction.EAST;
            second = this.secondParts != null && state.hasProperty(DummyableBlock.TYPE) && !DummyableBlock.isCore(state);
            if(second) dir = dir.getClockWise();
        }

        int index = (dir.get2DDataValue() & 3) + (second ? 4 : 0);
        List<BakedQuad> quads = this.cache[index];
        if(quads != null) return quads;

        Matrix4f matrix = new Matrix4f();
        matrix.translate(0.5F, 0.0F, 0.5F);
        matrix.rotate(Axis.YP.rotationDegrees(angle(dir)));
        return this.cache[index] = this.bake(second ? this.secondParts : this.coreParts, matrix);
    }

    /** Items are drawn through the three-argument getQuads (ItemRenderer.renderModelLists). */
    @Override
    public List<BakedQuad> getQuads(@Nullable BlockState state, @Nullable Direction direction, RandomSource random) {
        return direction == null ? this.itemQuads() : Collections.emptyList();
    }

    /**
     * The item, turned as the original's inventory renderers turn it: the partitioner by 90 degrees about Y (RenderPartitioner.java:25);
     * the splitter shrunk to 0.625 and turned by -90 degrees, the core and the second block one block apart along the turned Z
     * (RenderSplitter.java:24-33).
     */
    private List<BakedQuad> itemQuads() {
        if(this.itemQuads != null) return this.itemQuads;

        if(this.secondParts == null) {
            Matrix4f matrix = new Matrix4f().translate(0.5F, 0.125F, 0.5F).rotate(Axis.YP.rotationDegrees(90F));
            return this.itemQuads = this.bake(this.coreParts, matrix);
        }

        List<BakedQuad> quads = new ArrayList<>();
        Matrix4f core = new Matrix4f().translate(0.5F, 0.1875F, 0.5F).scale(0.625F).rotate(Axis.YP.rotationDegrees(-90F)).translate(0F, 0F, 0.5F);
        Matrix4f second = new Matrix4f().translate(0.5F, 0.1875F, 0.5F).scale(0.625F).rotate(Axis.YP.rotationDegrees(-90F)).translate(0F, 0F, -0.5F);
        quads.addAll(this.bake(this.coreParts, core));
        quads.addAll(this.bake(this.secondParts, second));
        return this.itemQuads = quads;
    }

    private List<BakedQuad> bake(Map<String, TextureAtlasSprite> parts, Matrix4f matrix) {
        List<BakedQuad> quads = new ArrayList<>();
        for(Map.Entry<String, TextureAtlasSprite> part : parts.entrySet()) {
            quads.addAll(this.bakeSimpleQuads(List.of(part.getKey()), new Matrix4f(matrix), part.getValue()));
        }
        return quads;
    }

    @Override
    public ChunkRenderTypeSet getRenderTypes(@Nullable BlockState state, RandomSource rand, ModelData data) {
        return RENDER_TYPE;
    }

    @Override
    public TextureAtlasSprite getParticleIcon() {
        return this.particle;
    }
}
