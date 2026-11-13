package com.hbm.config;

import net.neoforged.neoforge.common.ModConfigSpec;

public class ServerConfig {

    public final ModConfigSpec.DoubleValue MINE_AP_DAMAGE;
    public final ModConfigSpec.DoubleValue MINE_HE_DAMAGE;
    public final ModConfigSpec.DoubleValue MINE_SHRAP_DAMAGE;
    public final ModConfigSpec.DoubleValue MINE_NUKE_DAMAGE;
    public final ModConfigSpec.DoubleValue MINE_NAVAL_DAMAGE;

    public final ModConfigSpec.BooleanValue TAINT_TRAILS;

    public final ModConfigSpec.BooleanValue CRATE_OPEN_HELD;
    public final ModConfigSpec.BooleanValue CRATE_KEEP_CONTENTS;

    public final ModConfigSpec.IntValue CONVEYOR_CRAM_MAX;
    public final ModConfigSpec.BooleanValue CONVEYOR_CRAM_EXPLODE;

    ServerConfig(ModConfigSpec.Builder builder) {

        MINE_AP_DAMAGE = builder
                .comment("Damage for anti-personell landmine.")
                .translation("hbmsntm.configuration.mine_ap_damage")
                .defineInRange("mine_ap_damage", 10F, 0, Double.MAX_VALUE);
        MINE_HE_DAMAGE = builder
                .comment("Damage for anti-tank landmine.")
                .translation("hbmsntm.configuration.mine_he_damage")
                .defineInRange("mine_he_damage", 35F, 0, Double.MAX_VALUE);
        MINE_SHRAP_DAMAGE = builder
                .comment("Damage for shrapnel landmine.")
                .translation("hbmsntm.configuration.mine_shrap_damage")
                .defineInRange("mine_shrap_damage", 7.5F, 0, Double.MAX_VALUE);
        MINE_NUKE_DAMAGE = builder
                .comment("Damage for fat landmine.")
                .translation("hbmsntm.configuration.mine_nuke_damage")
                .defineInRange("mine_nuke_damage", 100F, 0, Double.MAX_VALUE);
        MINE_NAVAL_DAMAGE = builder
                .comment("Damage for naval mine.")
                .translation("hbmsntm.configuration.mine_naval_damage")
                .defineInRange("mine_naval_damage", 60F, 0, Double.MAX_VALUE);

        TAINT_TRAILS = builder
                .comment("When turned on, taint effect will make trail.")
                .translation("hbmsntm.configuration.taint_trails")
                .define("taint_trails", false);

        CRATE_OPEN_HELD = builder
                .comment("When turned on, crates can be opened in hands.")
                .translation("hbmsntm.configuration.crate_open_held")
                .define("crate_open_held", true);

        CRATE_KEEP_CONTENTS = builder
                .comment("When turned on, crate will not drop their contents on break.")
                .translation("hbmsntm.configuration.crate_keep_contents")
                .define("crate_keep_contents", true);

        // Original ServerConfig.java:29-30
        CONVEYOR_CRAM_MAX = builder
                .comment("How many items or packages crammed together on a conveyor belt make them pop.")
                .translation("hbmsntm.configuration.conveyor_cram_max")
                .defineInRange("conveyor_cram_max", 25, 1, Integer.MAX_VALUE);

        CONVEYOR_CRAM_EXPLODE = builder
                .comment("When turned on, a crammed conveyor belt is destroyed along with the items.")
                .translation("hbmsntm.configuration.conveyor_cram_explode")
                .define("conveyor_cram_explode", true);
    }
}
