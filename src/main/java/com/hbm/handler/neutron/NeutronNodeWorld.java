package com.hbm.handler.neutron;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Original NeutronNodeWorld (:10-104). Keyed by the server level of the block entity that created the stream (GOAL24 decision 12);
 * client levels never get an entry. The cache must not outlive its level: NtmEventHandler removes a level on LevelEvent.Unload
 * (original ModEventHandler.onUnload) and clears everything on ServerStoppedEvent (NEO-only).
 */
public class NeutronNodeWorld {

    // List of all stream worlds.
    public static final Map<Level, StreamWorld> streamWorlds = new HashMap<>();

    public static NeutronNode getNode(Level level, BlockPos pos) {
        StreamWorld streamWorld = streamWorlds.get(level);
        return streamWorld != null ? streamWorld.nodeCache.get(pos) : null;
    }

    public static void removeNode(Level level, BlockPos pos) {
        StreamWorld streamWorld = streamWorlds.get(level);
        if(streamWorld == null) return;
        streamWorld.removeNode(pos);
    }

    public static StreamWorld getOrAddWorld(Level level) {
        StreamWorld streamWorld = streamWorlds.get(level);
        if(streamWorld == null) {
            streamWorld = new StreamWorld();
            streamWorlds.put(level, streamWorld);
        }
        return streamWorld;
    }

    /** NEO-only: drops the streams and nodes of an unloaded level (the original removes the map entry in ModEventHandler.onUnload). */
    public static void removeWorld(Level level) {
        streamWorlds.remove(level);
    }

    public static void removeAllWorlds() {
        streamWorlds.clear();
    }

    public static void removeEmptyWorlds() {
        streamWorlds.values().removeIf((streamWorld) -> {
            return streamWorld.streams.isEmpty();
        });
    }

    public static class StreamWorld {

        private List<NeutronStream> streams;
        // Keys are the immutable positions of the nodes (NeutronNode.pos); lookups may use mutable positions.
        private HashMap<BlockPos, NeutronNode> nodeCache = new HashMap<>();

        public StreamWorld() {
            streams = new ArrayList<>();
        }

        public void runStreamInteractions(Level level) {
            for(NeutronStream stream : streams) {
                stream.runStreamInteraction(level, this);
            }
        }

        public void addStream(NeutronStream stream) {
            streams.add(stream);
        }

        public void removeAllStreams() {
            streams.clear();
        }

        public void cleanNodes() {
            List<BlockPos> toRemove = new ArrayList<>();
            for(NeutronNode cachedNode : nodeCache.values()) {
                if(cachedNode.type == NeutronStream.NeutronType.RBMK) {
                    RBMKNeutronHandler.RBMKNeutronNode node = (RBMKNeutronHandler.RBMKNeutronNode) cachedNode;
                    toRemove.addAll(node.checkNode(this));
                }
                /* TODO: actually do this and uncache pile nodes
                if(cachedNode.type == NeutronStream.NeutronType.PILE) {
                    PileNeutronNode node = (PileNeutronNode) cachedNode;
                    toRemove.addAll(node.checkNode());
                }
                */
                // (NEO: the Chicago Pile and its PILE nodes are not migrated.)
            }

            for(BlockPos pos : toRemove) {
                nodeCache.remove(pos);
            }
        }

        public NeutronNode getNode(BlockPos pos) {
            return nodeCache.get(pos);
        }

        public void addNode(NeutronNode node) {
            nodeCache.put(node.pos, node);
        }

        public void removeNode(BlockPos pos) {
            nodeCache.remove(pos);
        }

        public void removeAllStreamsOfType(NeutronStream.NeutronType type) {
            streams.removeIf(stream -> stream.type == type);
        }
    }
}
