package com.hbm.inventory;

import com.hbm.main.NuclearTechMod;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.BlockTags;
import net.minecraft.tags.ItemTags;
import net.minecraft.tags.TagKey;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.levelgen.structure.Structure;


// Basically new ore dict and its vanilla
// Registration in datagens
@Deprecated
public class NtmTags {

    public static class Blocks {
        public static final TagKey<Block> ACTUALLY_STONE = crateTag("actually_stone");
        public static final TagKey<Block> GROUND = crateTag("ground");
        public static final TagKey<Block> PLANTS = crateTag("plants");

        private static TagKey<Block> crateTag(String name) {
            return BlockTags.create(NuclearTechMod.withDefaultNamespace(name));
        }
    }

    public static class Structures {
        /** Structures whose chunks an oil bubble skips, see OilBubbleFeature. Data packs may append to it. */
        public static final TagKey<Structure> OIL_BUBBLE_AVOID = TagKey.create(Registries.STRUCTURE, NuclearTechMod.withDefaultNamespace("oil_bubble_avoid"));
    }

    public static class Items {

        public static final TagKey<Item> DUSTS_ALUMINIUM = commonTag("dusts/aluminum");
        public static final TagKey<Item> ORES_ALUMINIUM = commonTag("ores/aluminum");
        public static final TagKey<Item> PLATES_STEEL = commonTag("plates/steel");
        public static final TagKey<Item> PLATES_COPPER = commonTag("plates/copper");

        /*
         * TANKS
         */
        public static final TagKey<Item> UNIVERSAL_TANK = crateTag("ntm_universal_tank");
        public static final TagKey<Item> HAZARD_TANK = crateTag("ntm_hazard_tank");
        public static final TagKey<Item> UNIVERSAL_BARREL = crateTag("ntm_universal_barrel");

        private static TagKey<Item> crateTag(String name) {
            return ItemTags.create(NuclearTechMod.withDefaultNamespace(name));
        }
        private static TagKey<Item> commonTag(String name) {
            return ItemTags.create(ResourceLocation.fromNamespaceAndPath("c", name));
        }
    }
}
