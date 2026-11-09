package com.hbm.main;

import api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache;
import com.hbm.blockentity.machine.MachineRadarBlockEntity;
import com.hbm.blockentity.network.RTTYSystem;
import com.hbm.config.NtmConfig;
import com.hbm.extprop.HbmPlayerAttachments;
import com.hbm.handler.neutron.NeutronHandler;
import com.hbm.handler.neutron.NeutronNodeWorld;
import com.hbm.network.toclient.InformPlayer;
import com.hbm.registry.NtmDamageTypes;
import com.hbm.saveddata.satellite.SatelliteDetector;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.TagsUtil;
import com.hbm.world.MeteorStrikeSystem;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.entity.living.LivingEntityUseItemEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.event.level.LevelEvent;
import net.neoforged.neoforge.event.server.ServerStoppedEvent;
import net.neoforged.neoforge.event.tick.LevelTickEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.network.PacketDistributor;

import java.util.ArrayList;

@EventBusSubscriber(modid = NuclearTechMod.MODID)
public class NtmEventHandler {

    @SubscribeEvent
    public static void onPlayerLogin(PlayerEvent.PlayerLoggedInEvent event) {
        Player player = event.getEntity();
        Level level = player.level;

        if(!level.isClientSide) {

            if(NtmConfig.COMMON.ENABLE_MOTD.get()) {
                player.sendSystemMessage(Component.translatable("message.hbmsntm.loaded", Component.translatable("message.hbmsntm.neo").withStyle(ChatFormatting.LIGHT_PURPLE), NuclearTechMod.VERSION));
            }

            if(NtmConfig.COMMON.ENABLE_DUCKS.get() && !HbmPlayerAttachments.getData(player).ducked) {
                if(player instanceof ServerPlayer serverPlayer) PacketDistributor.sendToPlayer(serverPlayer, new InformPlayer(Component.translatable("info.duck"), NuclearTechModClient.ID_DUCK, 30_000));
            }
        }
    }

    // ModEventHandler.onFoodEaten (ModEventHandler.java:1339-1350): food marked "ntmCyanide" by AnvilSmithingCyanideRecipe kills the eater
    // with ten 1,000-point hits, each randomly euthanizedSelf or euthanizedSelf2. The event's item is a copy taken before the food was eaten.
    @SubscribeEvent
    public static void onFoodEaten(LivingEntityUseItemEvent.Finish event) {
        if(!(event.getEntity() instanceof Player player) || player.level().isClientSide) return;

        ItemStack stack = event.getItem();

        if(stack.getItem().getFoodProperties(stack, player) != null && TagsUtil.getCustomData(stack).getBoolean("ntmCyanide")) {
            for(int i = 0; i < 10; i++) {
                player.hurt(player.damageSources().source(player.getRandom().nextBoolean() ? NtmDamageTypes.EUTHANIZED_SELF : NtmDamageTypes.EUTHANIZED_SELF_2), 1000);
            }
        }
    }

    @SubscribeEvent
    public static void onServerTick(ServerTickEvent.Pre event) {

        // Redstone over Radio
        RTTYSystem.updateBroadcastQueue(event.getServer());
        // Networks! All of them!
        UniNodespace.updateNodespace(event.getServer());
        // Radar entry handling
        MachineRadarBlockEntity.updateSystem(event.getServer());
        // Meteor strike handling
        MeteorStrikeSystem.update(event.getServer());
        // RBMK neutron streams of the last tick (original NeutronHandler on ServerTickEvent START)
        NeutronHandler.onServerTick(event.getServer());
    }

    @SubscribeEvent
    public static void levelTick(LevelTickEvent.Pre event) {

        SatelliteDetector.updateSystem(event.getLevel());
    }

    @SubscribeEvent
    public static void onLevelUnload(LevelEvent.Unload event) {
        if(event.getLevel() instanceof Level level) {
            UniNodespace.removeLevel(level);
            BlockEntityAccessCache.clearLevel(level);
            // Neutron streams and nodes of the level (original ModEventHandler.onUnload)
            NeutronNodeWorld.removeWorld(level);
        }
    }

    @SubscribeEvent
    public static void onServerStopped(ServerStoppedEvent event) {
        for(Level level : new ArrayList<>(UniNodespace.levels.keySet())) UniNodespace.removeLevel(level);
        BlockEntityAccessCache.cache.clear();
        // NEO-only: the original never clears the neutron cache on stop; an integrated server would keep its stale levels
        NeutronNodeWorld.removeAllWorlds();
    }
}
