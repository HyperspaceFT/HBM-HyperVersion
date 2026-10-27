package com.hbm.blockentity.machine;

import api.hbm.block.ICrucibleAcceptor;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.material.MaterialShapes;
import com.hbm.inventory.material.Mats;
import net.minecraft.Util;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.state.BlockState;

import java.util.ArrayList;
import java.util.List;

/**
 * Upstream TileEntityFoundryTank (foundry storage basin): every 5-10 ticks fills the tank below, otherwise flows into a neighbouring
 * non-channel acceptor, otherwise spreads into neighbouring tanks.
 */
public class FoundryTankBlockEntity extends FoundryBaseBlockEntity {

    public int nextUpdate;

    public FoundryTankBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.FOUNDRY_TANK.get(), pos, state);
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;

        if(!this.level.isClientSide) {

            if(this.type == null && this.amount != 0) {
                this.amount = 0;
            }

            nextUpdate--;

            if(nextUpdate <= 0 && this.amount > 0 && this.type != null) {

                boolean hasOp = false;
                nextUpdate = this.level.random.nextInt(6) + 5;

                if(this.level.getBlockEntity(this.worldPosition.below()) instanceof FoundryTankBlockEntity tank) {

                    if((tank.type == null || tank.type == this.type) && tank.amount < tank.getCapacity()) {
                        tank.type = this.type;
                        int toFill = Math.min(this.amount, tank.getCapacity() - tank.amount);
                        this.amount -= toFill;
                        tank.amount += toFill;
                        tank.setChanged();
                        this.setChanged();
                        hasOp = true;
                    }
                }

                List<Integer> ints = new ArrayList<>(List.of(2, 3, 4, 5));
                Util.shuffle(ints, this.level.random);

                if(!hasOp) {

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
                                } else {
                                    this.amount = left.amount;
                                }
                                hasOp = true;
                                this.setChanged();
                                break;
                            }
                        }
                    }
                }

                if(!hasOp) {
                    for(Integer i : ints) {
                        Direction dir = Direction.from3DDataValue(i);

                        if(this.level.getBlockEntity(this.worldPosition.relative(dir)) instanceof FoundryTankBlockEntity acc) {

                            if(acc.type == null || acc.type == this.type || acc.amount == 0) {
                                acc.type = this.type;
                                if(this.level.random.nextInt(5) == 0) {
                                    //1:4 chance that the fill states are simply swapped
                                    //this promotes faster spreading and prevents spread limits
                                    int buf = this.amount;
                                    this.amount = acc.amount;
                                    acc.amount = buf;

                                } else {
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
        }

        super.updateEntity();
    }

    @Override
    public int getCapacity() {
        return MaterialShapes.BLOCK.q(4);
    }
}
