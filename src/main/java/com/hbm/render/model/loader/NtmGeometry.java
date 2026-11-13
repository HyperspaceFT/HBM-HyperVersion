package com.hbm.render.model.loader;

import com.hbm.render.loader.HFRWavefrontObject;
import com.hbm.blocks.machine.NTMAnvilBlock;
import com.hbm.render.model.*;
import net.minecraft.client.renderer.block.model.BakedQuad;
import net.minecraft.client.renderer.block.model.ItemOverrides;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.client.resources.model.BakedModel;
import net.minecraft.client.resources.model.Material;
import net.minecraft.client.resources.model.ModelBaker;
import net.minecraft.client.resources.model.ModelState;
import net.minecraft.core.Direction;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.client.model.data.ModelData;
import net.neoforged.neoforge.client.model.geometry.IGeometryBakingContext;
import net.neoforged.neoforge.client.model.geometry.IUnbakedGeometry;

import org.joml.Matrix4f;

import javax.annotation.Nullable;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;

public class NtmGeometry implements IUnbakedGeometry<NtmGeometry> {

    public enum BakedModelType {
        BARBED_WIRE,
        SPIKES,
        BARREL,
        CABLE,
        DET_CORD,
        PIPE,
        ANVIL,
        RBMK_DEBRIS,
        RBMK_ELEMENT,
        PAINTABLE_CABLE,
        PAINTABLE_DUCT,
        CRANE_SPLITTER,
        CRANE_PARTITIONER
    }

    private final BakedModelType type;

    public NtmGeometry(BakedModelType type) {
        this.type = type;
    }

    @Override
    public BakedModel bake(IGeometryBakingContext context, ModelBaker baker, Function<Material, TextureAtlasSprite> spriteGetter, ModelState state, ItemOverrides overrides) {

        TextureAtlasSprite textureSprite = null;
        TextureAtlasSprite overlaySprite = null;

        if(context.hasMaterial("texture")) textureSprite = spriteGetter.apply(context.getMaterial("texture"));
        if(context.hasMaterial("overlay")) overlaySprite = spriteGetter.apply(context.getMaterial("overlay"));

        return switch(this.type) {
            case BARBED_WIRE -> new BarbedWireBakedModel(new HFRWavefrontObject("models/obj/block/barbed_wire.obj"), textureSprite);
            case SPIKES -> new SimpleWavefrontBakedModel(new HFRWavefrontObject("models/obj/block/spikes.obj"), textureSprite);
            case BARREL -> new SimpleWavefrontBakedModel(new HFRWavefrontObject("models/obj/block/barrel.obj"), textureSprite);
            case CABLE -> new CableBakedModel(new HFRWavefrontObject("models/obj/block/cable_neo.obj"), textureSprite);
            case DET_CORD -> new DetCordBakedModel(new HFRWavefrontObject("models/obj/block/cable_neo.obj"), textureSprite);
            case PIPE -> new PipeNeoBakedModel(new HFRWavefrontObject("models/obj/block/pipe_neo.obj"), textureSprite, overlaySprite);
            case ANVIL -> new AnvilBakedModel(new HFRWavefrontObject("models/obj/block/anvil.obj"), textureSprite);
            // paintable cable: red_cable_base with red_cable_overlay, painted or not (BlockCablePaintable.java:53-70)
            case PAINTABLE_CABLE -> new PaintableBakedModel(textureSprite, overlaySprite, false, overlaySprite);
            // paintable duct: the fluid-coloured overlay while unpainted, the plain port overlay over a paint (FluidDuctPaintable.java:54-92)
            case PAINTABLE_DUCT -> new PaintableBakedModel(textureSprite, spriteGetter.apply(context.getMaterial("overlay_color")), true, overlaySprite);
            case RBMK_DEBRIS -> new SimpleWavefrontBakedModel(new HFRWavefrontObject("models/obj/rbmk/debris.obj"), textureSprite);
            // original ResourceManager.java:1713-1714 load both with noSmooth(); NEO's noSmooth() has no effect (S_Face ignores the
            // flag) and both OBJs carry flat per-face normals, so it is not called
            case CRANE_SPLITTER -> new ConveyorObjBakedModel(new HFRWavefrontObject("models/obj/block/splitter.obj"),
                    splitterParts(context, spriteGetter, true), splitterParts(context, spriteGetter, false),
                    spriteGetter.apply(context.getMaterial("particle")), context.getTransforms());
            case CRANE_PARTITIONER -> new ConveyorObjBakedModel(new HFRWavefrontObject("models/obj/block/crane_buffer.obj"),
                    namedParts(context, spriteGetter, "Side", "side", "Back", "back", "Top_Top.001", "top", "Inner", "inner", "InnerSide", "inner_side", "Belt", "belt"),
                    null, spriteGetter.apply(context.getMaterial("side")), context.getTransforms());
            // The fuel channel body; "fuel" is the rod texture of its item form. The display transforms come from the model's parent.
            // rbmk_element.obj mixes triangles and quads inside its "Cap" group, so it is read in mixed mode as the original
            // ResourceManager.java:1675 does; the baker emits each face by its own vertex count (Goal 24 acceptance D1).
            case RBMK_ELEMENT -> new RBMKElementBakedModel(new HFRWavefrontObject("models/obj/rbmk/rbmk_element.obj", true), new HFRWavefrontObject("models/obj/rbmk/rbmk_element_rods.obj"),
                    spriteGetter.apply(context.getMaterial("side")), spriteGetter.apply(context.getMaterial("top")), spriteGetter.apply(context.getMaterial("inner")),
                    spriteGetter.apply(context.getMaterial("fuel")), context.getTransforms());
        };
    }

    /** OBJ group to the sprite of a named material, in pairs (RenderPartitioner.java:61-69). */
    private static Map<String, TextureAtlasSprite> namedParts(IGeometryBakingContext context, Function<Material, TextureAtlasSprite> spriteGetter, String... pairs) {
        Map<String, TextureAtlasSprite> parts = new LinkedHashMap<>();
        for(int i = 0; i < pairs.length; i += 2) parts.put(pairs[i], spriteGetter.apply(context.getMaterial(pairs[i + 1])));
        return parts;
    }

    /** RenderSplitter.java:61-74: the left half (the core) or the right half (the second block) of the splitter. */
    private static Map<String, TextureAtlasSprite> splitterParts(IGeometryBakingContext context, Function<Material, TextureAtlasSprite> spriteGetter, boolean left) {
        return namedParts(context, spriteGetter,
                "Top", left ? "top_left" : "top_right",
                "Bottom", left ? "top_right" : "top_left",
                left ? "Left" : "Right", left ? "left" : "right",
                "Back", left ? "back_left" : "back_right",
                "Front", left ? "front_left" : "front_right",
                "Inner", "inner",
                "InnerLeft", "inner_side",
                "InnerRight", "inner_side",
                "InnerTop", "inner_side",
                "InnerBottom", "belt");
    }
}
