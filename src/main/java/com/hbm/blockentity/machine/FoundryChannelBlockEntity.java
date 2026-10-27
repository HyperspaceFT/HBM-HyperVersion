package com.hbm.blockentity.machine;

import api.hbm.block.ICrucibleAcceptor;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.material.MaterialShapes;
import com.hbm.inventory.material.Mats;
import com.hbm.uninos.UniNodespace;
import com.hbm.uninos.networkproviders.FoundryNetworkProvider;
import com.hbm.uninos.networkproviders.FoundryNode;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.Util;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

import java.util.ArrayList;
import java.util.List;

/**
 * Upstream TileEntityFoundryChannel: every 5 ticks flows into a neighbouring non-channel acceptor, otherwise spreads into neighbouring
 * channels. Channels form a node network so a pour can be refused when the network already carries another material.
 */
public class FoundryChannelBlockEntity extends FoundryBaseBlockEntity {

    public int nextUpdate;
    /** 3D data value (2-5, N/S/W/E like upstream's ForgeDirection ordinals) of the side the last inflow came from; 0 = none. */
    public int lastFlow = 0;

    protected FoundryNode node;

    public FoundryChannelBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.FOUNDRY_CHANNEL.get(), pos, state);
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;

        if(!this.level.isClientSide) {
            this.initNode();

            if(this.node.type != null && this.amount == 0) {
                this.node.type = null;
            }

            if(this.type == null && this.amount != 0) {
                this.amount = 0;
            }

            nextUpdate--;

            if(nextUpdate <= 0 && this.amount > 0 && this.type != null) {

                boolean hasOp = false;
                nextUpdate = 5;

                List<Integer> ints = new ArrayList<>(List.of(2, 3, 4, 5));
                Util.shuffle(ints, this.level.random);
                if(lastFlow > 0) {
                    ints.remove((Integer) this.lastFlow);
                    ints.add(this.lastFlow);
                }

                for(Integer i : ints) {
                    Direction dir = Direction.from3DDataValue(i);
                    BlockPos neighbor = this.worldPosition.relative(dir);
                    BlockState state = this.level.getBlockState(neighbor);

                    if(state.getBlock() instanceof ICrucibleAcceptor acc && !state.is(NtmBlocks.FOUNDRY_CHANNEL.get())) {

                        if(acc.canAcceptPartialFlow(this.level, neighbor, dir.getOpposite(), new Mats.MaterialStack(this.type, this.amount))) {
                            Mats.MaterialStack left = acc.flow(this.level, neighbor, dir.getOpposite(), new Mats.MaterialStack(this.type, this.amount));
                            if(left == null) {
                                this.type = null;
                                this.amount = 0;

                                this.node.type = null;
                            } else {
                                this.amount = left.amount;
                            }
                            hasOp = true;
                            this.setChanged();
                            break;
                        }
                    }
                }

                if(!hasOp) {
                    for(Integer i : ints) {
                        Direction dir = Direction.from3DDataValue(i);

                        if(this.level.getBlockEntity(this.worldPosition.relative(dir)) instanceof FoundryChannelBlockEntity acc) {

                            if(acc.type == null || acc.type == this.type || acc.amount == 0) {
                                acc.type = this.type;
                                acc.initNode();
                                acc.node.type = this.type;

                                acc.lastFlow = dir.getOpposite().get3DDataValue();

                                if(this.level.random.nextInt(5) == 0 || this.amount == 1) { //force swap operations with single quanta to keep them moving
                                    //1:4 chance that the fill states are simply swapped
                                    //this promotes faster spreading and prevents spread limits
                                    int buf = this.amount;
                                    this.amount = acc.amount;
                                    acc.amount = buf;

                                } else {
                                    //otherwise, equalize the neighbors
                                    int diff = this.amount - acc.amount;

                                    if(diff > 0) {
                                        diff /= 2;
                                        this.amount -= diff;
                                        acc.amount += diff;
                                    }
                                }

                                acc.setChanged();
                                this.setChanged();
                            }
                        }
                    }
                }
            }

            if(this.amount == 0) {
                if(this.lastFlow != 0) this.setChanged();
                this.lastFlow = 0;
                this.nextUpdate = 5;
            }
        }

        super.updateEntity();
    }

    protected void initNode() {
        if(this.node == null || this.node.expired) {

            this.node = (FoundryNode) UniNodespace.getNode(this.level, this.worldPosition, FoundryNetworkProvider.THE_PROVIDER);

            if(this.node == null || this.node.expired) {
                this.node = this.createNode();
                this.node.type = this.type;
                UniNodespace.createNode(this.level, this.node);
            }
        }
    }

    public FoundryNode createNode() {
        return new FoundryNode(FoundryNetworkProvider.THE_PROVIDER, this.worldPosition).setConnections(
                new DirPos(this.worldPosition.east(), Direction.EAST),
                new DirPos(this.worldPosition.west(), Direction.WEST),
                new DirPos(this.worldPosition.south(), Direction.SOUTH),
                new DirPos(this.worldPosition.north(), Direction.NORTH)
        );
    }

    @Override
    public int getCapacity() {
        return MaterialShapes.INGOT.q(2);
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.lastFlow = tag.getByte("flow");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putByte("flow", (byte) this.lastFlow);
    }

    /** Upstream destroys the node on invalidate; 1.21 calls setRemoved for both removal and chunk unload (PipeBaseBlockEntity precedent). */
    @Override
    public void setRemoved() {
        super.setRemoved();

        if(this.level != null && !this.level.isClientSide) {
            if(this.node != null) {
                UniNodespace.destroyNode(this.level, this.worldPosition, FoundryNetworkProvider.THE_PROVIDER);
            }
        }
    }

    @Override
    public boolean canAcceptPartialPour(Level level, BlockPos pos, Vec3 hit, Direction side, Mats.MaterialStack stack) {
        if(this.node == null || !this.node.hasValidNet()) return false;
        for(FoundryNode node : this.node.net.links) {
            if(node.type != null && node.type != stack.material) {
                return false;
            }
        }

        return super.canAcceptPartialPour(level, pos, hit, side, stack);
    }

    @Override
    public Mats.MaterialStack flow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) {
        if(this.node != null) this.node.type = stack.material;
        return super.flow(level, pos, side, stack);
    }

    @Override
    public Mats.MaterialStack pour(Level level, BlockPos pos, Vec3 hit, Direction side, Mats.MaterialStack stack) {
        if(this.node != null) this.node.type = stack.material;
        return super.pour(level, pos, hit, side, stack);
    }
}
