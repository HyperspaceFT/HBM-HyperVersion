package com.hbm.handler.neutron;

import com.hbm.blockentity.machine.rbmk.IRBMKFluxReceiver;
import com.hbm.blockentity.machine.rbmk.RBMKAbsorberBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKBaseBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKControlBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKDials;
import com.hbm.blockentity.machine.rbmk.RBMKOutgasserBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKRodBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKType;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock;
import com.hbm.handler.neutron.NeutronNodeWorld.StreamWorld;
import com.hbm.handler.radiation.ChunkRadiationManager;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

/**
 * Original RBMKNeutronHandler (:20-429). The column type is the 24A enum {@link RBMKType}. Not migrated yet: the ReaSim rods
 * (Goal 26); their branches are left as comments where they sit. The control rods arrived in Goal24D, the outgasser in Goal25B.
 */
public class RBMKNeutronHandler {

    // Set by NeutronHandler every server tick before the streams run; public so that a test driving a stream directly can set them.
    public static double moderatorEfficiency;
    public static double reflectorEfficiency;
    public static double absorberEfficiency;
    public static int columnHeight;
    public static int fluxRange;

    // Like the original Compat.getTileStandard this never loads a chunk.
    private static BlockEntity blockPosToTE(Level level, BlockPos pos) {
        return level.isLoaded(pos) ? level.getBlockEntity(pos) : null;
    }

    /** The cached node of the column, or a new one that is not added to the cache yet. */
    public static RBMKNeutronNode makeNode(StreamWorld streamWorld, RBMKBaseBlockEntity tile) {
        BlockPos pos = tile.getBlockPos();
        RBMKNeutronNode node = (RBMKNeutronNode) streamWorld.getNode(pos);
        return node != null ? node : new RBMKNeutronNode(tile, tile.getRBMKType(), tile.hasLid());
    }

    public static class RBMKNeutronNode extends NeutronNode {

        // The original keeps these two in the node's data map ("hasLid", "type").
        private boolean hasLid;
        private final RBMKType rbmkType;

        public RBMKNeutronNode(RBMKBaseBlockEntity tile, RBMKType type, boolean hasLid) {
            super(tile, NeutronStream.NeutronType.RBMK);
            this.hasLid = hasLid;
            this.rbmkType = type;
            posInstance = tile.getBlockPos().mutable();
        }

        public void addLid() {
            this.hasLid = true;
        }

        public void removeLid() {
            this.hasLid = false;
        }

        public boolean hasLid() {
            return this.hasLid;
        }

        public RBMKType getRBMKType() {
            return this.rbmkType;
        }

        protected BlockPos.MutableBlockPos posInstance;

        private int x;
        private int z;

        // Used for every node by checkNode, not only for ReaSim rods; the name and the arithmetic are the original's.
        public Iterator<BlockPos> getReaSimNodes() {

            x = -fluxRange;
            z = -fluxRange;

            return new Iterator<BlockPos>() {
                @Override
                public boolean hasNext() {
                    return (fluxRange + x) * (fluxRange * 2 + 1) + z + fluxRange + 1 < (fluxRange * 2 + 1) * (fluxRange * 2 + 1);
                }

                @Override
                public BlockPos next() {
                    if(Math.pow(x, 2) + Math.pow(z, 2) <= fluxRange * fluxRange) {
                        z++;
                        if(z > fluxRange) {
                            z = -fluxRange;
                            x++;
                        }
                        return posInstance.set(pos.getX() + x, pos.getY(), pos.getZ() + z);
                    } else {
                        z++;
                        if(z > fluxRange) {
                            z = -fluxRange;
                            x++;
                        }
                        return null;
                    }
                }
            };
        }

        public List<BlockPos> checkNode(StreamWorld streamWorld) {
            List<BlockPos> list = new ArrayList<>();

            BlockPos pos = this.tile.getBlockPos();

            RBMKNeutronStream[] streams = new RBMKNeutronStream[RBMKRodBlockEntity.fluxDirs.length];

            // Simulate streams coming out of the RBMK rod.
            Direction[] fluxDirs = RBMKRodBlockEntity.fluxDirs;
            for(int i = 0; i < fluxDirs.length; i++) {
                streams[i] = (new RBMKNeutronStream(this, new Vec3(fluxDirs[i].getStepX(), 0, fluxDirs[i].getStepZ())));
            }

            // Check if the rod should uncache nodes.
            if(tile instanceof RBMKRodBlockEntity rod) {
                if(!rod.hasRod || rod.lastFluxQuantity == 0) {

                    for(RBMKNeutronStream stream : streams) {
                        for(NeutronNode node : stream.getNodes(streamWorld, false))
                            if(node != null)
                                list.add(node.tile.getBlockPos());
                    }

                    return list;
                }
            }

            // Original :130-144: a ReaSim rod without a rod or flux uncaches every node of its circle. ReaSim is not migrated (Goal 26).

            // Check if non-rod nodes should be uncached... but now with ReaSim!
            { //  Yeah, I don't want to contaminate the surrounding scope.
                Iterator<BlockPos> reaSimNodes = getReaSimNodes();

                boolean hasRod = false;

                while(reaSimNodes.hasNext()) {

                    BlockPos nodePos = reaSimNodes.next();

                    if(nodePos == null)
                        continue;

                    NeutronNode node = streamWorld.getNode(nodePos);

                    if(node != null && node.tile instanceof RBMKRodBlockEntity rod) {

                        if(rod.hasRod && rod.lastFluxQuantity > 0) {
                            hasRod = true;
                            break;
                        }
                    }
                }

                if(!hasRod) {
                    list.add(pos);
                    return list;
                }
            }

            // Check if non-rod nodes should be uncached due to no rod in range.
            for(RBMKNeutronStream stream : streams) {

                NeutronNode[] nodes = stream.getNodes(streamWorld, false);

                for(NeutronNode node : nodes) {
                    if(!(node == null) && node.tile instanceof RBMKRodBlockEntity)
                        return list;
                }
            }

            // If we get here, then no rods were found along this stream's path!
            // This, most of the time, means we can just uncache all the nodes inside the stream's path.
            // That other part of the time, streams will be crossing paths.
            // This is fine though, we can just uncache them anyway and the streams later on (next tick) will recache them.
            //  /\ idk what this guy was on about but this is just plain wrong. /\
            list.add(pos);

            return list;
        }
    }


    public static class RBMKNeutronStream extends NeutronStream {

        public RBMKNeutronStream(NeutronNode origin, Vec3 vector) {
            super(origin, vector);
        }

        public RBMKNeutronStream(NeutronNode origin, Vec3 vector, double flux, double ratio) {
            super(origin, vector, flux, ratio, NeutronType.RBMK);
        }

        // Does NOT include the origin node
        // USES THE CACHE!!!
        public NeutronNode[] getNodes(StreamWorld streamWorld, boolean addNode) {
            NeutronNode[] positions = new RBMKNeutronNode[fluxRange];

            BlockPos.MutableBlockPos pos = origin.tile.getBlockPos().mutable();
            Level level = origin.tile.getLevel();

            for(int i = 1; i <= fluxRange; i++) {
                int x = (int) Math.floor(0.5 + vector.x * i);
                int z = (int) Math.floor(0.5 + vector.z * i);

                pos.set(origin.pos.getX() + x, origin.pos.getY(), origin.pos.getZ() + z);

                NeutronNode node = streamWorld.getNode(pos);
                if(node instanceof RBMKNeutronNode) {
                    positions[i - 1] = node;
                } else if(this.origin.tile.getBlockState().getBlock() instanceof RBMKBaseBlock) {
                    BlockEntity te = blockPosToTE(level, pos);
                    if(te instanceof RBMKBaseBlockEntity rbmkBase) {
                        node = makeNode(streamWorld, rbmkBase);
                        positions[i - 1] = node;
                        if(addNode) streamWorld.addNode(node);
                    }
                }
            }
            return positions;
        }

        // The... small one? whatever it's still pretty big, runs the interaction for the stream.
        @Override
        public void runStreamInteraction(Level level, StreamWorld streamWorld) {

            // do nothing if there's nothing to do lmao
            if(fluxQuantity == 0D)
                return;

            BlockPos pos = origin.tile.getBlockPos();

            RBMKBaseBlockEntity originTE;

            NeutronNode node = streamWorld.getNode(pos);
            if(node != null) {
                originTE = (RBMKBaseBlockEntity) node.tile;
            } else {
                BlockEntity tile = blockPosToTE(level, pos);
                if(!(tile instanceof RBMKBaseBlockEntity)) return; // Doesn't exist anymore!
                originTE = (RBMKBaseBlockEntity) tile;

                streamWorld.addNode(new RBMKNeutronNode(originTE, originTE.getRBMKType(), originTE.hasLid()));
            }

            int moderatedCount = 0;

            Iterator<BlockPos> iterator = getBlocks(fluxRange);

            while(iterator.hasNext()) {

                BlockPos targetPos = iterator.next();

                if(fluxQuantity == 0D) // Whoops, used it all up!
                    return;

                // NEO-only: in 1.7.10 every loaded tile entity ticks. Here a column in a loaded chunk outside the block-ticking range does
                // not, so it would bank the flux of every tick and burn it all at once when its chunk ticks again; and getHits would load
                // an unloaded chunk. The stream ends at such a position, as at the edge of the loaded world.
                if(!level.shouldTickBlocksAt(targetPos))
                    return;

                NeutronNode targetNode = streamWorld.getNode(targetPos);
                if(targetNode == null) {
                    BlockEntity te = blockPosToTE(level, targetPos); // ok, maybe it didn't get added to the list somehow??
                    if(te instanceof RBMKBaseBlockEntity rbmk) {
                        targetNode = makeNode(streamWorld, rbmk);
                        streamWorld.addNode(targetNode); // whoops!
                    } else {
                        int hits = getHits(targetPos); // Get the amount of hits on blocks.
                        if(hits == columnHeight) // If stream is fully blocked.
                            return;
                        else if(hits > 0) { // If stream is partially blocked.
                            // The original irradiates the origin position here, not the target (kept).
                            irradiateFromFlux(pos, hits);
                            fluxQuantity *= 1 - ((double) hits / columnHeight); // Inverse to get partial blocking by blocks.
                            continue;
                        } else { // Nothing hit!
                            irradiateFromFlux(pos, 0);
                            continue;
                        }
                    }
                }

                RBMKType type = ((RBMKNeutronNode) targetNode).getRBMKType();

                if(type == RBMKType.OTHER || type == null) // pass right on by!
                    continue;

                // we established earlier during `getNodes()` that they should all be RBMKBase TEs
                // no issue with casting here!
                RBMKBaseBlockEntity nodeTE = (RBMKBaseBlockEntity) targetNode.tile;

                if(!((RBMKNeutronNode) targetNode).hasLid())
                    ChunkRadiationManager.proxy.incrementRad(level, targetPos, (float) (this.fluxQuantity * 0.05F));

                if(type == RBMKType.MODERATOR || nodeTE.isModerated()) {
                    moderatedCount++;
                    moderateStream();
                }

                if(nodeTE instanceof IRBMKFluxReceiver) {
                    IRBMKFluxReceiver column = (IRBMKFluxReceiver) nodeTE;

                    if(type == RBMKType.ROD) {
                        RBMKRodBlockEntity rod = (RBMKRodBlockEntity) column;

                        // An empty fuel channel lets the stream pass on.
                        if(rod.hasRod) {
                            rod.receiveFlux(this);
                            return;
                        }

                    } else if(type == RBMKType.OUTGASSER) {
                        // Original :323-329. Only RBMKOutgasserBlockEntity reports OUTGASSER; a channel that cannot process lets the
                        // stream pass on.
                        RBMKOutgasserBlockEntity outgasser = (RBMKOutgasserBlockEntity) column;

                        if(outgasser.canProcess()) {
                            column.receiveFlux(this);
                            return;
                        }
                    }

                } else if(type == RBMKType.CONTROL_ROD) {
                    // Original :332-340. The control columns are no IRBMKFluxReceiver, so this branch is reached as in the original.
                    RBMKControlBlockEntity rod = (RBMKControlBlockEntity) nodeTE;

                    if(rod.level > 0.0D) {

                        this.fluxQuantity *= rod.getMult();
                        continue;
                    }
                    return;
                } else if(type == RBMKType.REFLECTOR) {

                    if(((RBMKBaseBlockEntity) this.origin.tile).isModerated())
                        moderatedCount++;

                    if(this.fluxRatio > 0 && moderatedCount > 0)
                        for(int i = 0; i < moderatedCount; i++)
                            moderateStream();

                    if(reflectorEfficiency != 1.0D) {
                        this.fluxQuantity *= reflectorEfficiency;
                        continue;
                    }

                    // The original casts to TileEntityRBMKRod (GOAL24 decision 12: the interface is the same call for a fuel column). Streams
                    // start at fuel columns, but an origin re-resolved from the world above can be another column that replaced the rod
                    // between two ticks; the original's cast then crashes the server. NEO drops the reflected flux at an origin that is no
                    // IRBMKFluxReceiver; an irradiation channel there takes it only while it can process (its own receiveFlux check).
                    if(originTE instanceof IRBMKFluxReceiver receiver)
                        receiver.receiveFlux(this);
                    return;
                } else if(type == RBMKType.ABSORBER) {
                    ((RBMKAbsorberBlockEntity) nodeTE).heat += RBMKDials.getAbsorberHeatConversion() * this.fluxQuantity;

                    if(absorberEfficiency == 1)
                        return;

                    this.fluxQuantity *= absorberEfficiency;
                }
            }

            NeutronNode[] nodes = getNodes(streamWorld, true);

            NeutronNode lastNode = nodes[(nodes.length - 1)];

            if(lastNode == null) { // This implies that there was *no* last node, meaning either way it was never caught.
                // There is really no good way to figure out where exactly it should irradiate, so just irradiate at the origin tile.
                irradiateFromFlux(BlockPos.containing(origin.pos.getX() + this.vector.x, origin.pos.getY(), origin.pos.getZ() + this.vector.z));
                return;
            }

            // Original :377-397.
            RBMKType lastNodeType = ((RBMKNeutronNode) lastNode).getRBMKType();

            if(lastNodeType == RBMKType.CONTROL_ROD) {
                RBMKControlBlockEntity rod = (RBMKControlBlockEntity) lastNode.tile;
                if(rod.getMult() > 0.0D) {
                    this.fluxQuantity *= rod.getMult();
                    BlockPos lastPos = lastNode.tile.getBlockPos();
                    BlockPos posAfter = BlockPos.containing(lastPos.getX() + this.vector.x, lastPos.getY(), lastPos.getZ() + this.vector.z);

                    // The below code checks if the block after the control rod is actually a block or if it's an RBMK rod.
                    // Resolves GitHub issue #1933.
                    // (Upstream-shared: the original checks `pos`, the stream's origin, whose node always exists while the stream
                    // runs, so this block practically never runs. Kept as the original.)
                    if(NeutronNodeWorld.getNode(level, pos) == null) {
                        BlockEntity te = blockPosToTE(level, posAfter);
                        if(te instanceof RBMKBaseBlockEntity rbmk) {
                            StreamWorld world = NeutronNodeWorld.getOrAddWorld(level);
                            RBMKNeutronNode nodeAfter = makeNode(world, rbmk);
                            world.addNode(nodeAfter);
                        } else {
                            irradiateFromFlux(posAfter); // I'm so mad about this...
                        }
                    }
                }
            }
        }

        public int getHits(BlockPos pos) {
            int hits = 0;

            for(int h = 0; h < columnHeight; h++) {
                // holy fucking shit
                // I have had this one line cause me like tens of problems
                // I FUCKING HATE THIS
                // total count of bugs fixed attributed to this function: 14
                // (NEO: 1.7.10 Block.isOpaqueCube, a full opaque cube, is isSolidRender here.)
                Level level = origin.tile.getLevel();
                BlockPos above = pos.above(h);
                BlockState state = level.getBlockState(above);
                if(state.isSolidRender(level, above))
                    hits += 1;
            }

            return hits;
        }

        public void irradiateFromFlux(BlockPos pos) {
            ChunkRadiationManager.proxy.incrementRad(origin.tile.getLevel(), pos, (float) (fluxQuantity * 0.05F * (1 - (double) getHits(pos) / columnHeight)));
        }

        public void irradiateFromFlux(BlockPos pos, int hits) {
            ChunkRadiationManager.proxy.incrementRad(origin.tile.getLevel(), pos, (float) (fluxQuantity * 0.05F * (1 - (double) hits / columnHeight)));
        }

        public void moderateStream() {
            fluxRatio *= (1 - moderatorEfficiency);
        }

    }
}
