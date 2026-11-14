package com.hbm.acceptance;

import com.mojang.logging.LogUtils;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import org.slf4j.Logger;

import java.nio.file.Path;

/**
 * Acceptance executor: a client-only mod that the dev client run loads beside hbmsntm (build.gradle loadedMods) and that
 * no other run or the release jar contains. Without {@code -Dhbm.accept.dir=<directory>} it registers nothing. With it,
 * {@link Executor} reads step files from that directory every client tick and writes one result file per step; the
 * format is in tools/migration/acceptance/README.md. It registers no blocks, items, data or payloads and never writes the
 * world itself: anything that changes the game goes through the same paths a player's input or chat would take.
 */
@Mod(value = AcceptanceMod.MOD_ID, dist = Dist.CLIENT)
public final class AcceptanceMod {
    public static final String MOD_ID = "hbmaccept";
    public static final Logger LOGGER = LogUtils.getLogger();

    public AcceptanceMod(IEventBus modBus) {
        String dir = System.getProperty("hbm.accept.dir");
        if (dir == null || dir.isBlank()) {
            LOGGER.info("hbmaccept: inactive (no -Dhbm.accept.dir)");
            return;
        }
        LOGGER.info("hbmaccept: active, step directory {}", dir);
        NeoForge.EVENT_BUS.register(new Executor(Path.of(dir)));
    }
}
