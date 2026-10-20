package com.hbm.handler.neutron;

import com.hbm.blockentity.machine.rbmk.RBMKDials;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.Level;

import java.util.Map;


// General neutron handler because I didn't feel like having each handler class have its own interaction function.
/**
 * Original NeutronHandler (:12-50). The original subscribes to TickEvent.ServerTickEvent phase START; NEO calls
 * {@link #onServerTick(MinecraftServer)} from NtmEventHandler on ServerTickEvent.Pre, so the streams created while the levels
 * ticked during tick N run at the start of tick N + 1, as in the original.
 */
public class NeutronHandler {

    private static int ticks = 0;

    public static void onServerTick(MinecraftServer server) {

        // Freshen the node cache every `cacheTime` ticks to prevent huge RAM usage from idle nodes.
        int cacheTime = 20;
        boolean cacheClear = ticks >= cacheTime;
        if(cacheClear) ticks = 0;
        ticks++;

        // Remove `StreamWorld` objects if they have no streams.
        NeutronNodeWorld.removeEmptyWorlds();

        for(Map.Entry<Level, NeutronNodeWorld.StreamWorld> world : NeutronNodeWorld.streamWorlds.entrySet()) {

            // Gamerule caching because this apparently is kinda slow?
            // meh, good enough
            // (NEO: the dials are common config values, the same for every level.)
            RBMKNeutronHandler.reflectorEfficiency = RBMKDials.getReflectorEfficiency();
            RBMKNeutronHandler.absorberEfficiency = RBMKDials.getAbsorberEfficiency();
            RBMKNeutronHandler.moderatorEfficiency = RBMKDials.getModeratorEfficiency();

            // I hate this.
            // this broke everything because it was ONE OFF
            // IT'S NOT THE TOTAL HEIGHT IT'S THE AMOUNT OF BLOCKS ABOVE AAAAAAAAAAAAA
            RBMKNeutronHandler.columnHeight = RBMKDials.getColumnHeight() + 1;
            RBMKNeutronHandler.fluxRange = RBMKDials.getFluxRange();

            world.getValue().runStreamInteractions(world.getKey());
            world.getValue().removeAllStreams();

            if(cacheClear) world.getValue().cleanNodes();
        }
    }
}
