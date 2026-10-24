package com.hbm.config;

import com.hbm.lib.ModEffect;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.config.ModConfig;
import net.neoforged.neoforge.common.ModConfigSpec;
import org.apache.commons.lang3.tuple.Pair;

import java.util.Locale;

public class NtmConfig {
    // COMMON
    public static final CommonConfig COMMON;
    public static final ModConfigSpec COMMON_SPEC;

    // SERVER
    public static final ServerConfig SERVER;
    public static final ModConfigSpec SERVER_SPEC;

    // CLIENT
    public static final ClientConfig CLIENT;
    public static final ModConfigSpec CLIENT_SPEC;

    static {
        // COMMON
        Pair<CommonConfig, ModConfigSpec> commonPair = new ModConfigSpec.Builder().configure(CommonConfig::new);
        COMMON = commonPair.getLeft();
        COMMON_SPEC = commonPair.getRight();

        // SERVER
        Pair<ServerConfig, ModConfigSpec> serverPair = new ModConfigSpec.Builder().configure(ServerConfig::new);
        SERVER = serverPair.getLeft();
        SERVER_SPEC = serverPair.getRight();

        // CLIENT
        Pair<ClientConfig, ModConfigSpec> clientPair = new ModConfigSpec.Builder().configure(ClientConfig::new);
        CLIENT = clientPair.getLeft();
        CLIENT_SPEC = clientPair.getRight();
    }

    public static void register(ModContainer container) {
        container.registerConfig(ModConfig.Type.COMMON, COMMON_SPEC);
        container.registerConfig(ModConfig.Type.SERVER, SERVER_SPEC);
        container.registerConfig(ModConfig.Type.CLIENT, CLIENT_SPEC);
    }

    // the funny
    public static boolean enable528() { return NtmConfig.COMMON.ENABLE_528.get(); }
    public static boolean true528() { return NtmConfig.COMMON.ENABLE_528.get() && NtmConfig.COMMON.ENABLE_528_MACHINE_GRAVITY.get(); }

    public static boolean enable528MachineGravity() { return NtmConfig.COMMON.ENABLE_528.get() && NtmConfig.COMMON.ENABLE_528_MACHINE_GRAVITY.get(); }

    public static boolean enableLBSM() { return !NtmConfig.COMMON.ENABLE_528.get() && NtmConfig.COMMON.ENABLE_LBSM.get(); }

    // Potion sickness. Original PotionConfig.java:40-45 (parse) and VersatileConfig.java:17-28 (apply / has).
    /** 1 for "NORMAL", 2 for "TERRARIA" (case-insensitive), anything else (default "OFF") 0 = potion sickness is turned off. */
    public static int potionSickness() {
        String mode = NtmConfig.COMMON.POTION_SICKNESS.get().toLowerCase(Locale.US);
        if(mode.equals("normal")) return 1;
        if(mode.equals("terraria")) return 2;
        return 0;
    }

    /** Applies potion sickness for {@code duration} seconds (x12 in TERRARIA mode); does nothing when it is turned off. */
    public static void applyPotionSickness(LivingEntity entity, int duration) {
        int mode = potionSickness();
        if(mode == 0) return;
        if(mode == 2) duration *= 12;

        MobEffectInstance sickness = new MobEffectInstance(ModEffect.POTIONSICKNESS, duration * 20);
        // The original passes an empty curative item list (setCurativeItems(new ArrayList())), so milk cannot remove the effect;
        // the 1.21 counterpart is an empty cure set, which also keeps the totem of undying from clearing it
        // (NeoForge's default cures are milk and the totem; honey only cures poison).
        sickness.getCures().clear();
        entity.addEffect(sickness);
    }

    public static boolean hasPotionSickness(LivingEntity entity) { return entity.hasEffect(ModEffect.POTIONSICKNESS); }
}
