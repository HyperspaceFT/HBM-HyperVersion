package com.hbm.config;

import net.neoforged.neoforge.common.ModConfigSpec;
import net.neoforged.neoforge.common.ModConfigSpec.BooleanValue;
import net.neoforged.neoforge.common.ModConfigSpec.ConfigValue;
import net.neoforged.neoforge.common.ModConfigSpec.DoubleValue;
import net.neoforged.neoforge.common.ModConfigSpec.IntValue;

import java.util.Set;

// YES im making one class for every config
public class CommonConfig {

    // GENERAL (01)
    public final BooleanValue ENABLE_DEBUG_MODE;
    public final BooleanValue ENABLE_MOTD;
    public final BooleanValue ENABLE_EXTENDED_LOGGING;
    public final BooleanValue ENABLE_BOMBER_SHORT_MODE;
    public final BooleanValue ENABLE_SILENT_COMPSTACK_ERRORS;
    public final BooleanValue ENABLE_KEYBIND_OVERLAP;
    public final BooleanValue ENABLE_EXPLOSION_EFFECTS;
    public final BooleanValue ENABLE_MACHINE_GRAVITY;

    public final BooleanValue ENABLE_EXPENSIVE_MODE;

    // NUKES (03)
    public final IntValue GADGET_RADIUS;
    public final IntValue BOY_RADIUS;
    public final IntValue MAN_RADIUS;
    public final IntValue MIKE_RADIUS;
    public final IntValue TSAR_RADIUS;
    public final IntValue PROTOTYPE_RADIUS;
    public final IntValue FLEIJA_RADIUS;
    public final IntValue SOLINIUM_RADIUS;
    public final IntValue N2_RADIUS;
    public final IntValue MISSLE_RADIUS;
    public final IntValue MIRV_RADIUS;
    public final IntValue FATMAN_RADIUS;
    public final IntValue NUKA_RADIUS;
    public final IntValue ASCHRAB_RADIUS;

    // METEORS (05)
    public final BooleanValue ENABLE_METEOR_STRIKES;
    public final BooleanValue ENABLE_METEOR_SHOWERS;
    public final BooleanValue ENABLE_METEOR_TAILS;
    public final BooleanValue ENABLE_SPECIAL_METEORS;
    public final IntValue METEOR_STRIKE_CHACE;
    public final IntValue METEOR_SHOWER_CHACE;
    public final IntValue METEOR_SHOWER_DURATION;

    // EXPLOSIONS (06)
    public final IntValue MK5;
    public final IntValue BLAST_SPEED;
    public final IntValue FALLOUT_RANGE;
    public final IntValue FALLOUT_DELAY;
    public final IntValue LIMIT_EXPLOSION_LIFESPAN;

    // DANGEROUS DROPS (10)
    public final BooleanValue DROP_CELL;
    public final BooleanValue DROP_SINGULARITY;
    public final BooleanValue DROP_STAR;
    public final BooleanValue DROP_CRYSTAL;
    public final BooleanValue DROP_DEAD_MANS_EXPLOSIVE;

    // TOOLS (11)
    public final IntValue RECURSION_DEPTH;
    public final BooleanValue RECURSION_STONE;
    public final BooleanValue RECURSION_NETHERRACK;
    public final BooleanValue ABILITY_HAMMER;
    public final BooleanValue ABILITY_VEIN;
    public final BooleanValue ABILITY_LUCK;
    public final BooleanValue ABILITY_SILK;
    public final BooleanValue ABILITY_FURNACE;
    public final BooleanValue ABILITY_SHREDDER;
    public final BooleanValue ABILITY_CENTRIFUGE;
    public final BooleanValue ABILITY_CRYSTALLIZER;
    public final BooleanValue ABILITY_MERCURY;
    public final BooleanValue ABILITY_EXPLOSION;

    // MOBS (12)
    public final BooleanValue ENABLE_DUCKS;

    public final DoubleValue POLLUTION_MULT;

    // RADIATION (13)
    public final IntValue FOG_RAD;
    public final IntValue FOG_RAD_CH;
    public final DoubleValue HELL_RAD;
    public final BooleanValue WORLD_RAD_EFFECTS;

    public final BooleanValue ENABLE_CONTAMINATION;
    public final BooleanValue ENABLE_CHUNK_RADS;

    public final BooleanValue ENABLE_SOOT_FOG;
    public final DoubleValue SOOT_FOG_THRESHOLD;
    public final DoubleValue SOOT_FOG_DIVISOR;

    // HAZARDS (14)
    public final BooleanValue DISABLE_ASBESTOS;
    public final BooleanValue DISABLE_COAL;
    public final BooleanValue DISABLE_HOT;
    public final BooleanValue DISABLE_EXPLOSIVE;
    public final BooleanValue DISABLE_HYDROACTIVE;
    public final BooleanValue DISABLE_BLINDING;

    // POTION (the original 8.S0_potionSickness, PotionConfig.java:22,40-45; read through NtmConfig.potionSickness())
    public final ConfigValue<String> POTION_SICKNESS;

    // RTG (the two RTG keys of the original 09_machines, MachineConfig.java:14-15)
    public final BooleanValue SCALE_RTG_POWER;
    public final BooleanValue DO_RTGS_DECAY;

    // RBMK (the original's per-world RBMK dial game rules, RBMKDials.java:17-51; read through RBMKDials)
    public final DoubleValue DIAL_PASSIVE_COOLING;
    public final DoubleValue DIAL_PASSIVE_COOLING_INNER;
    public final DoubleValue DIAL_COLUMN_HEAT_FLOW;
    public final DoubleValue DIAL_DIFFUSION_MOD;
    public final DoubleValue DIAL_HEAT_PROVISION;
    public final IntValue DIAL_COLUMN_HEIGHT;
    public final BooleanValue DIAL_ENABLE_PERMA_SCRAP;
    public final DoubleValue DIAL_BOILER_HEAT_CONSUMPTION;
    public final DoubleValue DIAL_CONTROL_SPEED;
    public final DoubleValue DIAL_REACTIVITY_MOD;
    public final DoubleValue DIAL_OUTGASSER_SPEED_MOD;
    public final DoubleValue DIAL_CONTROL_SURGE_MOD;
    public final IntValue DIAL_FLUX_RANGE;
    public final BooleanValue DIAL_DISABLE_MELTDOWNS;
    public final BooleanValue DIAL_ENABLE_MELTDOWN_OVERPRESSURE;
    public final DoubleValue DIAL_MODERATOR_EFFICIENCY;
    public final DoubleValue DIAL_ABSORBER_EFFICIENCY;
    public final DoubleValue DIAL_REFLECTOR_EFFICIENCY;
    public final BooleanValue DIAL_DISABLE_DEPLETION;
    public final BooleanValue DIAL_DISABLE_XENON;
    public final DoubleValue DIAL_ABSORBER_HEAT_CONVERSION;

    // POLLUTION (16)
    public final BooleanValue ENABLE_POLLUTION;

    // BIOMES (17)
    public final BooleanValue ENABLE_CRATER_BIOMES;
    public final DoubleValue CRATER_RAD;
    public final DoubleValue CRATER_INNER_RAD;
    public final DoubleValue CRATER_OUTER_RAD;
    public final DoubleValue CRATER_WATER_MULT;
    // WORLDGEN (the original 02_ores nether/end keys, WorldConfig.java:123-125,183-191, and 1.02_enablePlutoniumNetherOre, GeneralConfig.java:99)
    public final BooleanValue NETHER_ORES;
    public final BooleanValue END_ORES;
    public final BooleanValue ENABLE_PLUTONIUM_NETHER_ORE;
    public final IntValue NETHER_URANIUM_SPAWN_RATE;
    public final IntValue NETHER_TUNGSTEN_SPAWN_RATE;
    public final IntValue NETHER_SULFUR_SPAWN_RATE;
    public final IntValue NETHER_PHOSPHORUS_SPAWN_RATE;
    public final IntValue NETHER_COAL_SPAWN_RATE;
    public final IntValue NETHER_PLUTONIUM_SPAWN_RATE;
    public final IntValue NETHER_COBALT_SPAWN_RATE;
    public final IntValue END_TIKITE_SPAWN_RATE;
    // WORLDGEN, overworld (the original 02_ores keys, WorldConfig.java:121,127-147,176-179,193-195)
    public final BooleanValue OVERWORLD_ORES;
    public final IntValue GNEISS_IRON_SPAWN_RATE;
    public final IntValue GNEISS_GOLD_SPAWN_RATE;
    public final IntValue GNEISS_URANIUM_SPAWN_RATE;
    public final IntValue GNEISS_COPPER_SPAWN_RATE;
    public final IntValue GNEISS_ASBESTOS_SPAWN_RATE;
    public final IntValue GNEISS_LITHIUM_SPAWN_RATE;
    public final IntValue GNEISS_RARE_EARTH_SPAWN_RATE;
    public final IntValue GNEISS_GAS_SHALE_SPAWN_RATE;
    public final IntValue IRON_CLUSTER_SPAWN_RATE;
    public final IntValue TITANIUM_CLUSTER_SPAWN_RATE;
    public final IntValue ALUMINIUM_CLUSTER_SPAWN_RATE;
    public final IntValue COPPER_CLUSTER_SPAWN_RATE;
    public final IntValue ALEXANDRITE_SPAWN_RATE;
    public final BooleanValue ENABLE_HEMATITE;
    public final BooleanValue ENABLE_MALACHITE;
    public final BooleanValue ENABLE_BAUXITE;

    // 528
    public final BooleanValue ENABLE_528;
    public final BooleanValue ENABLE_528_MACHINE_GRAVITY;

    // LESS BULLSHIT MODE
    public final BooleanValue ENABLE_LBSM;

    CommonConfig(ModConfigSpec.Builder builder) {

        /// GENERAL ///
        builder.push("general");

        ENABLE_DEBUG_MODE = builder
                .comment("Enable debugging mode.")
                .translation("hbmsntm.configuration.enableDebugMode")
                .define("enableDebugMode", false);
        ENABLE_MOTD = builder
                .comment("If enabled, shows the 'Loaded mod!' chat message as well as update notifications when joining a world.")
                .translation("hbmsntm.configuration.enableMOTD")
                .define("enableMOTD", true);
        ENABLE_EXTENDED_LOGGING = builder
                .comment("Logs uses of the detonator, nuclear explosions, missile launches, grenades, etc.")
                .translation("hbmsntm.configuration.enableExtendedLogging")
                .define("enableExtendedLogging", true);
        ENABLE_BOMBER_SHORT_MODE = builder
                .comment("Has bomber planes spawn in closer to the target for use with smaller render distances.")
                .translation("hbmsntm.configuration.enableBomberShortMode")
                .define("enableBomberShortMode", false);
        ENABLE_SILENT_COMPSTACK_ERRORS = builder
                .comment("Enabling this will disable log spam created by unregistered items in ComparableStack instances.")
                .translation("hbmsntm.configuration.enableSilentCompStackErrors")
                .define("enableSilentCompStackErrors", false);
        ENABLE_KEYBIND_OVERLAP = builder
                .comment("If enabled, will handle keybinds that would otherwise be ignored due to overlapping.")
                .translation("hbmsntm.configuration.enableKeybindOverlap")
                .define("enableKeybindOverlap", true);
        ENABLE_EXPLOSION_EFFECTS = builder
                .comment("Toggles spawn of the old (new???) cloud particle when vanilla explosion effect occurs")
                .translation("hbmsntm.configuration.enableExplosionEffects")
                .define("enableExplosionEffects", true);
        ENABLE_MACHINE_GRAVITY = builder
                .comment("Requires large large machines to have a proper foundation, or else they tilt and break. Independent from the 528 version of this config, which does the same, but only works with 528 enabled")
                .translation("hbmsntm.configuration.enableMachineGravity")
                .define("enableMachineGravity", false);

        ENABLE_EXPENSIVE_MODE = builder
                .comment("It does what the name implies.")
                .translation("hbmsntm.configuration.enableExpensiveMode")
                .define("enableExpensiveMode", false);

        builder.pop();

        /// NUKES ///
        builder.push("nukes");

        GADGET_RADIUS = builder
                .comment("Radius of the Gadget.")
                .translation("hbmsntm.configuration.gadgetRadius")
                .defineInRange("gadgetRadius", 150, 0, Integer.MAX_VALUE);
        BOY_RADIUS = builder
                .comment("Radius of Little Boy.")
                .translation("hbmsntm.configuration.boyRadius")
                .defineInRange("boyRadius", 120, 0, Integer.MAX_VALUE);
        MAN_RADIUS = builder
                .comment("Radius of Fat Man.")
                .translation("hbmsntm.configuration.manRadius")
                .defineInRange("manRadius", 175, 0, Integer.MAX_VALUE);
        MIKE_RADIUS = builder
                .comment("Radius of Ivy Mike.")
                .translation("hbmsntm.configuration.mikeRadius")
                .defineInRange("mikeRadius", 250, 0, Integer.MAX_VALUE);
        TSAR_RADIUS = builder
                .comment("Radius of Tsar Bomba.")
                .translation("hbmsntm.configuration.tsarRadius")
                .defineInRange("tsarRadius", 500, 0, Integer.MAX_VALUE);
        PROTOTYPE_RADIUS = builder
                .comment("Radius of the Prototype.")
                .translation("hbmsntm.configuration.prototypeRadius")
                .defineInRange("prototypeRadius", 150, 0, Integer.MAX_VALUE);
        FLEIJA_RADIUS = builder
                .comment("Radius of F.L.E.I.J.A.")
                .translation("hbmsntm.configuration.fleijaRadius")
                .defineInRange("fleijaRadius", 50, 0, Integer.MAX_VALUE);
        SOLINIUM_RADIUS = builder
                .comment("Radius of the blue rinse.")
                .translation("hbmsntm.configuration.soliniumRadius")
                .defineInRange("soliniumRadius", 150, 0, Integer.MAX_VALUE);
        N2_RADIUS = builder
                .comment("Radius of the N2 mine.")
                .translation("hbmsntm.configuration.n2Radius")
                .defineInRange("n2Radius", 200, 0, Integer.MAX_VALUE);
        MISSLE_RADIUS = builder
                .comment("Radius of the nuclear missile")
                .translation("hbmsntm.configuration.missileRadius")
                .defineInRange("missileRadius", 100, 0, Integer.MAX_VALUE);
        MIRV_RADIUS = builder
                .comment("Radius of a MIRV.")
                .translation("hbmsntm.configuration.mirvRadius")
                .defineInRange("mirvRadius", 100, 0, Integer.MAX_VALUE);
        FATMAN_RADIUS = builder
                .comment("Radius of the Fatman Launcher.")
                .translation("hbmsntm.configuration.fatmanRadius")
                .defineInRange("fatmanRadius", 35, 0, Integer.MAX_VALUE);
        NUKA_RADIUS = builder
                .comment("Radius of the nuka grenade.")
                .translation("hbmsntm.configuration.nukaRadius")
                .defineInRange("nukaRadius", 25, 0, Integer.MAX_VALUE);
        ASCHRAB_RADIUS = builder
                .comment("Radius of dropped anti schrabidium.")
                .translation("hbmsntm.configuration.aSchrabRadius")
                .defineInRange("aSchrabRadius", 20, 0, Integer.MAX_VALUE);

        builder.pop();

        /// METEORS ///
        builder.push("explosion");

        ENABLE_METEOR_STRIKES = builder
                .comment("Toggles the spawning of meteors.")
                .translation("hbmsntm.configuration.enableMeteorStrikes")
                .define("enableMeteorStrikes", true);
        ENABLE_METEOR_SHOWERS = builder
                .comment("Toggles meteor showers, which start with a 1% chance for every spawned meteor.")
                .translation("hbmsntm.configuration.enableMeteorShowers")
                .define("enableMeteorShowers", true);
        ENABLE_METEOR_TAILS = builder
                .comment("Toggles the particle effect created by falling meteors.")
                .translation("hbmsntm.configuration.enableMeteorTails")
                .define("enableMeteorTails", true);
        ENABLE_SPECIAL_METEORS = builder
                .comment("Toggles rare, special meteor types with different impact effects.")
                .translation("hbmsntm.configuration.enableSpecialMeteors")
                .define("enableSpecialMeteors", true);
        METEOR_STRIKE_CHACE = builder
                .comment("The probability of a meteor spawning (an average of once every nTH ticks).")
                .translation("hbmsntm.configuration.meteorStrikeChance")
                .defineInRange("meteorStrikeChance", 40000, 1, Integer.MAX_VALUE);
        METEOR_SHOWER_CHACE = builder
                .comment("The probability of a meteor spawning during meteor shower (an average of once every nTH ticks).")
                .translation("hbmsntm.configuration.meteorShowerChance")
                .defineInRange("meteorShowerChance", 18000, 1, Integer.MAX_VALUE);
        METEOR_SHOWER_DURATION = builder
                .comment("Max duration of meteor shower in ticks.")
                .translation("hbmsntm.configuration.meteorShowerDuration")
                .defineInRange("meteorShowerDuration", 36000, 1, Integer.MAX_VALUE);

        builder.pop();

        /// EXPLOSIONS ///
        builder.push("explosion");

        MK5 = builder
                .comment("Minimum amount of milliseconds per tick allocated for mk5 chunk processing.")
                .translation("hbmsntm.configuration.mk5BlastTime")
                .defineInRange("mk5BlastTime", 50, 0, Integer.MAX_VALUE);
        BLAST_SPEED = builder
                .comment("Base speed of MK3 system (old and schrabidium) detonations (Blocks / tick)")
                .translation("hbmsntm.configuration.propBlastSpeed")
                .defineInRange("propBlastSpeed", 1024, 0, Integer.MAX_VALUE);
        FALLOUT_RANGE = builder
                .comment("Radius of fallout area (base radius * value in percent)")
                .translation("hbmsntm.configuration.falloutRange")
                .defineInRange("falloutRange", 100, 0, Integer.MAX_VALUE);
        FALLOUT_DELAY = builder
                .comment("How many ticks to wait for the next fallout chunk computation")
                .translation("hbmsntm.configuration.falloutDelay")
                .defineInRange("falloutDelay", 4, 0, Integer.MAX_VALUE);
        LIMIT_EXPLOSION_LIFESPAN = builder
                .comment("How long an explosion can be unloaded until it dies in seconds. Based of system time. 0 disables the effect.")
                .translation("hbmsntm.configuration.limitExplosionLifespan")
                .defineInRange("limitExplosionLifespan", 0, 0, Integer.MAX_VALUE);

        builder.pop();

        /// DANGEROUS DROPS ///
        builder.push("dangerous_drops");

        DROP_CELL = builder
                .comment("Whether antimatter cells should explode when dropped.")
                .translation("hbmsntm.configuration.dropCell")
                .define("dropCell", true);
        DROP_SINGULARITY = builder
                .comment("Whether singularities and black holes should spawn when dropped.")
                .translation("hbmsntm.configuration.dropSing")
                .define("dropSing", true);
        DROP_STAR = builder
                .comment("Whether rigged star blaster cells should explode when dropped.")
                .translation("hbmsntm.configuration.dropStar")
                .define("dropStar", true);
        DROP_CRYSTAL = builder
                .comment("Whether xen crystals should move blocks when dropped.")
                .translation("hbmsntm.configuration.dropCrys")
                .define("dropCrys", true);
        DROP_DEAD_MANS_EXPLOSIVE = builder
                .comment("Whether dead man's explosives should explode when dropped.")
                .translation("hbmsntm.configuration.dropDead")
                .define("dropDead", true);

        builder.pop();

        /// TOOLS ///
        builder.push("tools");

        RECURSION_DEPTH = builder
                .comment("Limits veinminer's recursive function")
                .translation("hbmsntm.configuration.recursionDepth")
                .defineInRange("recursionDepth", 1000, 0, Integer.MAX_VALUE);
        RECURSION_STONE = builder
                .comment("Determines whether veinminer can break stone")
                .translation("hbmsntm.configuration.recursionStone")
                .define("recursionStone", false);
        RECURSION_NETHERRACK = builder
                .comment("Determines whether veinminer can break netherrack")
                .translation("hbmsntm.configuration.recursionNetherrack")
                .define("recursionNetherrack", false);
        ABILITY_HAMMER = builder
                .comment("Allows AoE ability")
                .translation("hbmsntm.configuration.hammerAbility")
                .define("hammerAbility", true);
        ABILITY_VEIN = builder
                .comment("Allows veinminer ability")
                .translation("hbmsntm.configuration.abilityVein")
                .define("abilityVein", true);
        ABILITY_LUCK = builder
                .comment("Allow luck (fortune) ability")
                .translation("hbmsntm.configuration.abilityLuck")
                .define("abilityLuck", true);
        ABILITY_SILK = builder
                .comment("Allow silk touch ability")
                .translation("hbmsntm.configuration.abilitySilk")
                .define("abilitySilk", true);
        ABILITY_FURNACE = builder
                .comment("Allow auto-smelter ability")
                .translation("hbmsntm.configuration.abilityFurnace")
                .define("abilityFurnace", true);
        ABILITY_SHREDDER = builder
                .comment("Allow auto-shredder ability")
                .translation("hbmsntm.configuration.abilityShredder")
                .define("abilityShredder", true);
        ABILITY_CENTRIFUGE = builder
                .comment("Allow auto-centrifuge ability")
                .translation("hbmsntm.configuration.abilityCentrifuge")
                .define("abilityCentrifuge", true);
        ABILITY_CRYSTALLIZER = builder
                .comment("Allow auto-crystallizer ability")
                .translation("hbmsntm.configuration.abilityCrystallizer")
                .define("abilityCrystallizer", true);
        ABILITY_MERCURY = builder
                .comment("Allow mercury touch ability (digging redstone gives mercury)")
                .translation("hbmsntm.configuration.abilityMercury")
                .define("abilityMercury", true);
        ABILITY_EXPLOSION = builder
                .comment("Allow explosion ability")
                .translation("hbmsntm.configuration.abilityExplosion")
                .define("abilityExplosion", true);

        builder.pop();

        /// MOBS ///
        builder.push("mobs");

        ENABLE_DUCKS = builder
                .comment("Whether pressing O should allow the player to duck.")
                .translation("hbmsntm.configuration.enableDucks")
                .define("enableDucks", true);

        POLLUTION_MULT = builder
                .comment("A multiplier for soot emitted")
                .translation("hbmsntm.configuration.pollutionMult")
                .defineInRange("pollutionMult", 1.0, Double.MIN_VALUE, Double.MAX_VALUE);

        builder.pop();

        /// RADIATION ///
        builder.push("radiation");

        HELL_RAD = builder
                .comment("RAD/s in the nether.")
                .translation("hbmsntm.configuration.hellRad")
                .defineInRange("hellRad", 0.1D, 0, Double.MAX_VALUE);
        FOG_RAD = builder
                .comment("Radiation in RADs required for fog to spawn.")
                .translation("hbmsntm.configuration.fogRad")
                .defineInRange("fogRad", 100, 0, Integer.MAX_VALUE);
        FOG_RAD_CH = builder
                .comment("1:n chance of fog spawning every second.")
                .translation("hbmsntm.configuration.fogRadChance")
                .defineInRange("fogRadChance", 20, 0, Integer.MAX_VALUE);
        WORLD_RAD_EFFECTS = builder
                .comment("Whether high radiation levels should perform changes in the world.")
                .translation("hbmsntm.configuration.worldRadEffects")
                .define("worldRadEffects", true);

        ENABLE_CONTAMINATION = builder
                .comment("Toggles player contamination (and negative effects from radiation poisoning).")
                .translation("hbmsntm.configuration.enableContamination")
                .define("enableContamination", true);
        ENABLE_CHUNK_RADS = builder
                .comment("Toggles the world radiation system (chunk radiation only, some blocks use an AoE!).")
                .translation("hbmsntm.configuration.enableChunkRads")
                .define("enableChunkRads", true);

        ENABLE_SOOT_FOG = builder
                .comment("Whether smog should be visible")
                .translation("hbmsntm.configuration.enableSootFog")
                .define("enableSootFog", true);
        SOOT_FOG_THRESHOLD = builder
                .comment("How much soot is required for smog to become visible")
                .translation("hbmsntm.configuration.sootFogThreshold")
                .defineInRange("sootFogThreshold", 35.0, 0, Double.MAX_VALUE);
        SOOT_FOG_DIVISOR = builder
                .comment("The divisor for smog, higher numbers will require more soot for the same smog density")
                .translation("hbmsntm.configuration.sootFogDivisor")
                .defineInRange("sootFogDivisor", 120.0, 1.0, Double.MAX_VALUE);

        builder.pop();


        /// HAZARDS ///
        builder.push("hazards");

        DISABLE_ASBESTOS = builder
                .comment("When turned on, all asbestos hazards are disabled.")
                .translation("hbmsntm.configuration.disableAsbestos")
                .define("disableAsbestos", false);
        DISABLE_COAL = builder
                .comment("When turned on, all coal dust hazards are disabled.")
                .translation("hbmsntm.configuration.disableCoaldust")
                .define("disableCoaldust", false);
        DISABLE_HOT = builder
                .comment("When turned on, all hot hazards are disabled.")
                .translation("hbmsntm.configuration.disableHot")
                .define("disableHot", false);
        DISABLE_EXPLOSIVE = builder
                .comment("When turned on, all explosive hazards are disabled.")
                .translation("hbmsntm.configuration.disableExplosive")
                .define("disableExplosive", false);
        DISABLE_HYDROACTIVE = builder
                .comment("When turned on, all hydroactive hazards are disabled.")
                .translation("hbmsntm.configuration.disableHydroactive")
                .define("disableHydroactive", false);
        DISABLE_BLINDING = builder
                .comment("When turned on, all blinding hazards are disabled.")
                .translation("hbmsntm.configuration.disableBlinding")
                .define("disableBlinding", false);

        builder.pop();

        /// POTION ///
        // Original PotionConfig.java:22,40-45: option 8.S0_potionSickness (the numeric prefix is dropped like every NEO key), default
        // "OFF"; NtmConfig.potionSickness() parses it (NORMAL -> 1, TERRARIA -> 2, anything else -> 0 = off).
        builder.push("potion");

        POTION_SICKNESS = builder
                .comment("Valid configs include \"NORMAL\" and \"TERRARIA\", otherwise potion sickness is turned off")
                .translation("hbmsntm.configuration.potionSickness")
                .define("potionSickness", "OFF");

        builder.pop();

        /// RTG ///
        builder.push("rtg");

        SCALE_RTG_POWER = builder
                .comment("Should RTG/Betavoltaic fuel power scale down as it decays?")
                .translation("hbmsntm.configuration.scaleRTGPower")
                .define("scaleRTGPower", false);
        DO_RTGS_DECAY = builder
                .comment("Should RTG/Betavoltaic fuel decay at all?")
                .translation("hbmsntm.configuration.doRTGsDecay")
                .define("doRTGsDecay", true);

        builder.pop();

        /// RBMK ///
        // Original RBMKDials (:17-51 keys and defaults, :91-114 clamps, :157-375 comments): per-world game rules there, one
        // server config here. dialSaveDials does not apply; the three ReaSim dials are deferred with ReaSim.
        builder.push("rbmk");

        DIAL_PASSIVE_COOLING = builder
                .comment("Returns the amount of heat per tick removed from components passively, when at an edge")
                .translation("hbmsntm.configuration.dialPassiveCooling")
                .defineInRange("dialPassiveCooling", 2.5D, 0D, Double.MAX_VALUE);
        DIAL_PASSIVE_COOLING_INNER = builder
                .comment("Returns the amount of heat per tick removed from components passively, when surrounded by other components")
                .translation("hbmsntm.configuration.dialPassiveCoolingInner")
                .defineInRange("dialPassiveCoolingInner", 0.1D, 0D, Double.MAX_VALUE);
        DIAL_COLUMN_HEAT_FLOW = builder
                .comment("Returns the percentual step size how quickly neighboring component heat equalizes. 1 is instant, 0.5 is in 50% steps, et cetera.")
                .translation("hbmsntm.configuration.dialColumnHeatFlow")
                .defineInRange("dialColumnHeatFlow", 0.2D, 0D, 1D);
        DIAL_DIFFUSION_MOD = builder
                .comment("Returns a modifier for fuel rod diffusion, i.e. how quickly the core and hull temperatures equalize.")
                .translation("hbmsntm.configuration.dialDiffusionMod")
                .defineInRange("dialDiffusionMod", 1.0D, 0D, Double.MAX_VALUE);
        DIAL_HEAT_PROVISION = builder
                .comment("Returns the percentual step size how quickly the fuel hull heat and the component heat equalizes. 1 is instant, 0.5 is in 50% steps, et cetera.")
                .translation("hbmsntm.configuration.dialHeatProvision")
                .defineInRange("dialHeatProvision", 0.2D, 0D, 1D);
        DIAL_COLUMN_HEIGHT = builder
                .comment("Simple integer that decides how tall the structure is.", "Changing it does not resize columns that are already placed.")
                .translation("hbmsntm.configuration.dialColumnHeight")
                .defineInRange("dialColumnHeight", 4, 2, 16);
        DIAL_ENABLE_PERMA_SCRAP = builder
                .comment("Whether or not scrap entities despawn on their own or remain alive until picked up.")
                .translation("hbmsntm.configuration.dialEnablePermaScrap")
                .define("dialEnablePermaScrap", true);
        DIAL_BOILER_HEAT_CONSUMPTION = builder
                .comment("How many heat units are consumed per mB water used.")
                .translation("hbmsntm.configuration.dialBoilerHeatConsumption")
                .defineInRange("dialBoilerHeatConsumption", 0.1D, 0D, Double.MAX_VALUE);
        DIAL_CONTROL_SPEED = builder
                .comment("A multiplier for how quickly the control rods move.")
                .translation("hbmsntm.configuration.dialControlSpeed")
                .defineInRange("dialControlSpeed", 1.0D, 0D, Double.MAX_VALUE);
        DIAL_REACTIVITY_MOD = builder
                .comment("A multiplier for how much flux the rods give out.")
                .translation("hbmsntm.configuration.dialReactivityMod")
                .defineInRange("dialReactivityMod", 1.0D, 0D, Double.MAX_VALUE);
        // The original repeats the reactivity comment for the outgasser dial (RBMKDials.java:247-254).
        DIAL_OUTGASSER_SPEED_MOD = builder
                .comment("A multiplier for how much flux the rods give out.")
                .translation("hbmsntm.configuration.dialOutgasserSpeedMod")
                .defineInRange("dialOutgasserSpeedMod", 1.0D, 0D, Double.MAX_VALUE);
        DIAL_CONTROL_SURGE_MOD = builder
                .comment("A multiplier for how high the power surge goes when inserting control rods.")
                .translation("hbmsntm.configuration.dialControlSurgeMod")
                .defineInRange("dialControlSurgeMod", 1.0D, 0D, Double.MAX_VALUE);
        DIAL_FLUX_RANGE = builder
                .comment("Simple integer that decides how far the flux of a normal fuel rod reaches.")
                .translation("hbmsntm.configuration.dialFluxRange")
                .defineInRange("dialFluxRange", 5, 1, 100);
        DIAL_DISABLE_MELTDOWNS = builder
                .comment("Whether or not fuel columns should initiate a meltdown when overheating")
                .translation("hbmsntm.configuration.dialDisableMeltdowns")
                .define("dialDisableMeltdowns", false);
        DIAL_ENABLE_MELTDOWN_OVERPRESSURE = builder
                .comment("Whether or not connected pipes and turbines should explode when the reactor undergoes a meltdown.")
                .translation("hbmsntm.configuration.dialEnableMeltdownOverpressure")
                .define("dialEnableMeltdownOverpressure", false);
        DIAL_MODERATOR_EFFICIENCY = builder
                .comment("The percentage of neutrons to moderate from fast to slow when they pass through a moderator.")
                .translation("hbmsntm.configuration.dialModeratorEfficiency")
                .defineInRange("dialModeratorEfficiency", 1.0D, 0D, 1D);
        DIAL_ABSORBER_EFFICIENCY = builder
                .comment("The percentage of neutrons to be absorbed when a stream hits an absorber column.")
                .translation("hbmsntm.configuration.dialAbsorberEfficiency")
                .defineInRange("dialAbsorberEfficiency", 1.0D, 0D, 1D);
        DIAL_REFLECTOR_EFFICIENCY = builder
                .comment("The percentage of neutron to reflect when a stream hits a reflector column.")
                .translation("hbmsntm.configuration.dialReflectorEfficiency")
                .defineInRange("dialReflectorEfficiency", 1.0D, 0D, 1D);
        DIAL_DISABLE_DEPLETION = builder
                .comment("Whether fuel rods should deplete, disabling this makes rods last forever")
                .translation("hbmsntm.configuration.dialDisableDepletion")
                .define("dialDisableDepletion", false);
        DIAL_DISABLE_XENON = builder
                .comment("Whether xenon poison should be calculated")
                .translation("hbmsntm.configuration.dialDisableXenon")
                .define("dialDisableXenon", false);
        DIAL_ABSORBER_HEAT_CONVERSION = builder
                .comment("How many °C are generated per one flux that hits an absorber.")
                .translation("hbmsntm.configuration.dialAbsorberHeatConversion")
                .defineInRange("dialAbsorberHeatConversion", 0.05D, 0D, 1D);

        builder.pop();

        /// HAZARDS ///
        builder.push("pollution");

        ENABLE_POLLUTION = builder
                .comment("If disabled, none of the polltuion related things will work.")
                .translation("hbmsntm.configuration.enablePol")
                .define("enablePol", true);

        builder.pop();

        /// BIOMES ///
        builder.push("biomes");

        ENABLE_CRATER_BIOMES = builder
                .comment("Enables the biome change caused by nuclear explosions")
                .translation("hbmsntm.configuration.craterBiome")
                .define("craterBiome", true);
        CRATER_RAD = builder
                .comment("RAD/s for the crater biome")
                .translation("hbmsntm.configuration.craterBiomeRad")
                .defineInRange("craterBiomeRad", 5D, 0D, Double.MAX_VALUE);
        CRATER_INNER_RAD = builder
                .comment("RAD/s for the inner crater biome")
                .translation("hbmsntm.configuration.craterBiomeInnerRad")
                .defineInRange("craterBiomeInnerRad", 25D, 0D, Double.MAX_VALUE);
        CRATER_OUTER_RAD = builder
                .comment("RAD/s for the outer crater biome")
                .translation("hbmsntm.configuration.craterBiomeOuterRad")
                .defineInRange("craterBiomeOuterRad", 0.5D, 0D, Double.MAX_VALUE);
        CRATER_WATER_MULT = builder
                .comment("Multiplier for RAD/s in crater biomes when in water")
                .translation("hbmsntm.configuration.craterBiomeWaterMultiplier")
                .defineInRange("craterBiomeWaterMultiplier", 5D, 0D, Double.MAX_VALUE);

        builder.pop();

        /// WORLDGEN ///
        // Read by the hbmsntm:config_gated_add_features biome modifiers and the hbmsntm:config_count and hbmsntm:config_rarity
        // placements. Biome modifiers are applied once when the server starts, so changing a switch needs a restart; the counts
        // and rarities are read per chunk.
        builder.push("worldgen");

        NETHER_ORES = builder
                .comment("General switch for whether nether ores should be generated.")
                .translation("hbmsntm.configuration.worldgen.netherOres")
                .define("netherOres", true);
        END_ORES = builder
                .comment("General switch for whether end ores should be generated. Does not include special structures like trixite crystals.")
                .translation("hbmsntm.configuration.worldgen.endOres")
                .define("endOres", true);
        ENABLE_PLUTONIUM_NETHER_ORE = builder
                .comment("Enables plutonium ore generation in the nether")
                .translation("hbmsntm.configuration.worldgen.enablePlutoniumNetherOre")
                .define("enablePlutoniumNetherOre", false);
        NETHER_URANIUM_SPAWN_RATE = builder
                .comment("Amount of nether uranium per chunk")
                .translation("hbmsntm.configuration.worldgen.netherUraniumSpawnRate")
                .defineInRange("netherUraniumSpawnRate", 8, 0, 256);
        NETHER_TUNGSTEN_SPAWN_RATE = builder
                .comment("Amount of nether tungsten per chunk")
                .translation("hbmsntm.configuration.worldgen.netherTungstenSpawnRate")
                .defineInRange("netherTungstenSpawnRate", 10, 0, 256);
        NETHER_SULFUR_SPAWN_RATE = builder
                .comment("Amount of nether sulfur per chunk")
                .translation("hbmsntm.configuration.worldgen.netherSulfurSpawnRate")
                .defineInRange("netherSulfurSpawnRate", 26, 0, 256);
        NETHER_PHOSPHORUS_SPAWN_RATE = builder
                .comment("Amount of nether phosphorus per chunk")
                .translation("hbmsntm.configuration.worldgen.netherPhosphorusSpawnRate")
                .defineInRange("netherPhosphorusSpawnRate", 24, 0, 256);
        NETHER_COAL_SPAWN_RATE = builder
                .comment("Amount of nether coal per chunk")
                .translation("hbmsntm.configuration.worldgen.netherCoalSpawnRate")
                .defineInRange("netherCoalSpawnRate", 8, 0, 256);
        NETHER_PLUTONIUM_SPAWN_RATE = builder
                .comment("Amount of nether plutonium per chunk, if enabled")
                .translation("hbmsntm.configuration.worldgen.netherPlutoniumSpawnRate")
                .defineInRange("netherPlutoniumSpawnRate", 8, 0, 256);
        NETHER_COBALT_SPAWN_RATE = builder
                .comment("Amount of nether cobalt per chunk")
                .translation("hbmsntm.configuration.worldgen.netherCobaltSpawnRate")
                .defineInRange("netherCobaltSpawnRate", 2, 0, 256);
        END_TIKITE_SPAWN_RATE = builder
                .comment("Amount of end trixite per chunk")
                .translation("hbmsntm.configuration.worldgen.endTikiteSpawnRate")
                .defineInRange("endTikiteSpawnRate", 8, 0, 256);
        OVERWORLD_ORES = builder
                .comment("General switch for the schist ores, depth deposits and ore clusters. Does not include special structures like oil.")
                .translation("hbmsntm.configuration.worldgen.overworldOres")
                .define("overworldOres", true);
        // The original derives the schist uranium, copper, asbestos and gas shale counts from the plain ore keys (x3) and uses the
        // plain lithium and rare earth keys; NEO's plain ores are fixed JSON, so these keys hold the effective original counts
        GNEISS_IRON_SPAWN_RATE = builder
                .comment("Amount of schist iron ore veins per chunk")
                .translation("hbmsntm.configuration.worldgen.gneissIronSpawnRate")
                .defineInRange("gneissIronSpawnRate", 25, 0, 256);
        GNEISS_GOLD_SPAWN_RATE = builder
                .comment("Amount of schist gold ore veins per chunk")
                .translation("hbmsntm.configuration.worldgen.gneissGoldSpawnRate")
                .defineInRange("gneissGoldSpawnRate", 10, 0, 256);
        GNEISS_URANIUM_SPAWN_RATE = builder
                .comment("Amount of schist uranium ore veins per chunk")
                .translation("hbmsntm.configuration.worldgen.gneissUraniumSpawnRate")
                .defineInRange("gneissUraniumSpawnRate", 21, 0, 256);
        GNEISS_COPPER_SPAWN_RATE = builder
                .comment("Amount of schist copper ore veins per chunk")
                .translation("hbmsntm.configuration.worldgen.gneissCopperSpawnRate")
                .defineInRange("gneissCopperSpawnRate", 36, 0, 256);
        GNEISS_ASBESTOS_SPAWN_RATE = builder
                .comment("Amount of schist asbestos ore veins per chunk")
                .translation("hbmsntm.configuration.worldgen.gneissAsbestosSpawnRate")
                .defineInRange("gneissAsbestosSpawnRate", 6, 0, 256);
        GNEISS_LITHIUM_SPAWN_RATE = builder
                .comment("Amount of schist lithium ore veins per chunk")
                .translation("hbmsntm.configuration.worldgen.gneissLithiumSpawnRate")
                .defineInRange("gneissLithiumSpawnRate", 6, 0, 256);
        GNEISS_RARE_EARTH_SPAWN_RATE = builder
                .comment("Amount of schist rare earth ore veins per chunk")
                .translation("hbmsntm.configuration.worldgen.gneissRareEarthSpawnRate")
                .defineInRange("gneissRareEarthSpawnRate", 6, 0, 256);
        GNEISS_GAS_SHALE_SPAWN_RATE = builder
                .comment("Amount of gas shale veins per chunk")
                .translation("hbmsntm.configuration.worldgen.gneissGasShaleSpawnRate")
                .defineInRange("gneissGasShaleSpawnRate", 15, 0, 256);
        IRON_CLUSTER_SPAWN_RATE = builder
                .comment("Amount of iron cluster veins per chunk")
                .translation("hbmsntm.configuration.worldgen.ironClusterSpawnRate")
                .defineInRange("ironClusterSpawnRate", 4, 0, 256);
        TITANIUM_CLUSTER_SPAWN_RATE = builder
                .comment("Amount of titanium cluster veins per chunk")
                .translation("hbmsntm.configuration.worldgen.titaniumClusterSpawnRate")
                .defineInRange("titaniumClusterSpawnRate", 2, 0, 256);
        ALUMINIUM_CLUSTER_SPAWN_RATE = builder
                .comment("Amount of aluminium cluster veins per chunk")
                .translation("hbmsntm.configuration.worldgen.aluminiumClusterSpawnRate")
                .defineInRange("aluminiumClusterSpawnRate", 3, 0, 256);
        COPPER_CLUSTER_SPAWN_RATE = builder
                .comment("Amount of copper cluster veins per chunk")
                .translation("hbmsntm.configuration.worldgen.copperClusterSpawnRate")
                .defineInRange("copperClusterSpawnRate", 4, 0, 256);
        ALEXANDRITE_SPAWN_RATE = builder
                .comment("Spawns an alexandrite vein every nTH chunk")
                .translation("hbmsntm.configuration.worldgen.alexandriteSpawnRate")
                .defineInRange("alexandriteSpawnRate", 100, 0, 10000);
        ENABLE_HEMATITE = builder
                .comment("Toggles hematite deposits")
                .translation("hbmsntm.configuration.worldgen.enableHematite")
                .define("enableHematite", true);
        ENABLE_MALACHITE = builder
                .comment("Toggles malachite deposits")
                .translation("hbmsntm.configuration.worldgen.enableMalachite")
                .define("enableMalachite", true);
        ENABLE_BAUXITE = builder
                .comment("Toggles bauxite deposits")
                .translation("hbmsntm.configuration.worldgen.enableBauxite")
                .define("enableBauxite", true);

        builder.pop();

        /// 528 ///
        builder.comment("528 Mode: Please proceed with caution!");
        builder.comment("528-Modus: Lassen Sie Vorsicht walten!");
        builder.comment("способ-528: действовать с осторожностью!");
        builder.push("528");

        ENABLE_528 = builder
                .comment("The central toggle for 528 mode")
                .translation("hbmsntm.configuration.enable528")
                .define("enable528", false);
        ENABLE_528_MACHINE_GRAVITY = builder
                .comment("Requires most large machines to have a proper foundation, or else they tilt and break")
                .translation("hbmsntm.configuration.enable528MachineGravity")
                .define("enable528MachineGravity", true);

        builder.pop();

        /// LESS BULLSHIT MODE ///
        builder.comment("Will most likely break standard progression!");
        builder.comment("However, the game gets generally easier and more enjoyable for casual players.");
        builder.comment("Progression-braking recipes are usually not too severe, so the mode is generally server-friendly!");
        builder.push("LESS BULLSHIT MODE");

        ENABLE_LBSM = builder
                .comment("The central toggle for LBS mode. Forced OFF when 528 is enabled!")
                .translation("hbmsntm.configuration.enableLBSM")
                .define("enableLBSM", false);

        builder.pop();
    }

    /** The worldgen switch names a biome modifier may reference; the codec rejects any other name. */
    public static final Set<String> WORLDGEN_SWITCHES = Set.of("netherOres", "endOres", "enablePlutoniumNetherOre", "overworldOres",
            "enableHematite", "enableMalachite", "enableBauxite");
    /** The worldgen vein count names a placement may reference; the codec rejects any other name. */
    public static final Set<String> WORLDGEN_COUNTS = Set.of("netherUraniumSpawnRate", "netherTungstenSpawnRate", "netherSulfurSpawnRate",
            "netherPhosphorusSpawnRate", "netherCoalSpawnRate", "netherPlutoniumSpawnRate", "netherCobaltSpawnRate", "endTikiteSpawnRate",
            "gneissIronSpawnRate", "gneissGoldSpawnRate", "gneissUraniumSpawnRate", "gneissCopperSpawnRate", "gneissAsbestosSpawnRate",
            "gneissLithiumSpawnRate", "gneissRareEarthSpawnRate", "gneissGasShaleSpawnRate", "ironClusterSpawnRate",
            "titaniumClusterSpawnRate", "aluminiumClusterSpawnRate", "copperClusterSpawnRate");
    /** The worldgen "every nth chunk" names a placement may reference; the codec rejects any other name. */
    public static final Set<String> WORLDGEN_RARITIES = Set.of("alexandriteSpawnRate");

    /** The worldgen switch with this config key, or null for a name not in {@link #WORLDGEN_SWITCHES}. */
    public BooleanValue worldgenSwitch(String name) {
        return switch(name) {
            case "netherOres" -> NETHER_ORES;
            case "endOres" -> END_ORES;
            case "enablePlutoniumNetherOre" -> ENABLE_PLUTONIUM_NETHER_ORE;
            case "overworldOres" -> OVERWORLD_ORES;
            case "enableHematite" -> ENABLE_HEMATITE;
            case "enableMalachite" -> ENABLE_MALACHITE;
            case "enableBauxite" -> ENABLE_BAUXITE;
            default -> null;
        };
    }

    /** The worldgen vein count with this config key, or null for a name not in {@link #WORLDGEN_COUNTS}. */
    public IntValue worldgenCount(String name) {
        return switch(name) {
            case "netherUraniumSpawnRate" -> NETHER_URANIUM_SPAWN_RATE;
            case "netherTungstenSpawnRate" -> NETHER_TUNGSTEN_SPAWN_RATE;
            case "netherSulfurSpawnRate" -> NETHER_SULFUR_SPAWN_RATE;
            case "netherPhosphorusSpawnRate" -> NETHER_PHOSPHORUS_SPAWN_RATE;
            case "netherCoalSpawnRate" -> NETHER_COAL_SPAWN_RATE;
            case "netherPlutoniumSpawnRate" -> NETHER_PLUTONIUM_SPAWN_RATE;
            case "netherCobaltSpawnRate" -> NETHER_COBALT_SPAWN_RATE;
            case "endTikiteSpawnRate" -> END_TIKITE_SPAWN_RATE;
            case "gneissIronSpawnRate" -> GNEISS_IRON_SPAWN_RATE;
            case "gneissGoldSpawnRate" -> GNEISS_GOLD_SPAWN_RATE;
            case "gneissUraniumSpawnRate" -> GNEISS_URANIUM_SPAWN_RATE;
            case "gneissCopperSpawnRate" -> GNEISS_COPPER_SPAWN_RATE;
            case "gneissAsbestosSpawnRate" -> GNEISS_ASBESTOS_SPAWN_RATE;
            case "gneissLithiumSpawnRate" -> GNEISS_LITHIUM_SPAWN_RATE;
            case "gneissRareEarthSpawnRate" -> GNEISS_RARE_EARTH_SPAWN_RATE;
            case "gneissGasShaleSpawnRate" -> GNEISS_GAS_SHALE_SPAWN_RATE;
            case "ironClusterSpawnRate" -> IRON_CLUSTER_SPAWN_RATE;
            case "titaniumClusterSpawnRate" -> TITANIUM_CLUSTER_SPAWN_RATE;
            case "aluminiumClusterSpawnRate" -> ALUMINIUM_CLUSTER_SPAWN_RATE;
            case "copperClusterSpawnRate" -> COPPER_CLUSTER_SPAWN_RATE;
            default -> null;
        };
    }

    /** The worldgen "every nth chunk" value with this config key, or null for a name not in {@link #WORLDGEN_RARITIES}. */
    public IntValue worldgenRarity(String name) {
        return switch(name) {
            case "alexandriteSpawnRate" -> ALEXANDRITE_SPAWN_RATE;
            default -> null;
        };
    }
}
