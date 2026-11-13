package com.hbm.blockentity.network;

import api.hbm.fluidmk2.FluidNode;
import api.hbm.fluidmk2.IFluidPipeMK2;
import com.hbm.blockentity.IFluidCopiable;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.network.FluidDuctBaseBlock;
import com.hbm.blocks.network.FluidDuctConnectingBlock;
import com.hbm.blocks.network.IBlockFluidDuct;
import com.hbm.handler.HbmKeybinds.EnumKeybind;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.uninos.UniNodespace;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;

public class PipeBaseBlockEntity extends LoadedBaseBlockEntity implements IFluidPipeMK2, IFluidCopiable, ITickable {

    protected FluidNode node;
    protected FluidType type = Fluids.NONE;

    public PipeBaseBlockEntity(BlockPos pos, BlockState state) {
        this(NtmBlockEntityTypes.FLUID_DUCT.get(), pos, state);
    }

    protected PipeBaseBlockEntity(BlockEntityType<? extends PipeBaseBlockEntity> type, BlockPos pos, BlockState state) {
        super(type, pos, state);
    }

    @Override
    public void updateEntity() {
        if (level == null) return;

        if (!level.isClientSide) {
            if (this.node == null || this.node.expired) {

                if (this.shouldCreateNode()) {
                    this.node = (FluidNode) UniNodespace.getNode(this.level, this.worldPosition, type.getNetworkProvider());

                    if (this.node == null || this.node.expired) {
                        this.node = this.createNode(type);
                        UniNodespace.createNode(this.level, this.node);
                    }
                }
            }
        }

        this.networkPackNT(150);
    }

    public boolean shouldCreateNode() {
        return true;
    }

    public FluidType getFluidType() {
        return this.type;
    }

    public void setFluidType(FluidType type) {
        if (level == null) return;

        FluidType prev = this.type;
        this.type = type;
        this.setChanged();

        // The tint follows the type: re-render the block and notify clients, as the original's markBlockForUpdate (TileEntityPipeBaseNT.java:69-72)
        BlockState state = this.getBlockState();
        this.level.sendBlockUpdated(this.worldPosition, state, state, Block.UPDATE_CLIENTS);

        UniNodespace.destroyNode(this.level, this.worldPosition, prev.getNetworkProvider());

        if (this.node != null) {
            this.node = null;
        }
    }

    @Override
    public boolean canConnect(FluidType type, Direction dir) {
        return dir != null && type == this.type;
    }

    @Override
    public void setRemoved() {
        super.setRemoved();

        // A chunk unload calls onChunkUnloaded first and keeps the node, as the original destroys it only on invalidate; removing the block calls setRemoved alone
        // A reloaded block entity finds its kept node only on its first tick, so the node is destroyed by position
        if (this.level != null && !this.level.isClientSide && this.isLoaded) {
            UniNodespace.destroyNode(level, worldPosition, type.getNetworkProvider());
        }
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeInt(type.getID());
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        FluidType prev = this.type;
        this.type = Fluids.fromID(buf.readInt());
        // A new type that leaves the connections unchanged would not re-render the block, and the tint would keep the old colour
        if (prev != this.type && this.level != null) {
            BlockState state = this.getBlockState();
            this.level.sendBlockUpdated(this.worldPosition, state, state, Block.UPDATE_ALL_IMMEDIATE);
        }
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.type = Fluids.fromID(tag.getInt("Type"));
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putInt("Type", this.type.getID());
    }

    @Override
    public int[] getFluidIDToCopy() {
        return new int[]{ type.getID() };
    }

    @Override
    public FluidTank getTankToPaste() {
        return null;
    }

    /**
     * Original TileEntityPipeBaseNT.pasteSettings (:149-162): the copied fluid of the chosen entry, with TOOL_CTRL for the whole run of
     * pipes of this pipe's type. NEO pastes on the server only, treats a negative entry as an entry past the end (fluid 0, as the
     * original does for a too large one, where a negative one threw) and updates the pipe's connections after a single paste as the
     * identifier's right-click does.
     */
    @Override
    public void pasteSettings(CompoundTag tag, int index, Level level, Player player, BlockPos pos) {
        if(level.isClientSide) return;

        int[] ids = tag.getIntArray("FluidID");

        if (ids.length > 0) {
            int id;
            if (index >= 0 && index < ids.length) {
                id = ids[index];
            } else {
                id = 0;
            }

            FluidType fluid = Fluids.fromID(id);

            if (FluidDuctBaseBlock.isKeyPressed(player, EnumKeybind.TOOL_CTRL)) {
                if (level.getBlockState(this.worldPosition).getBlock() instanceof IBlockFluidDuct ibfd) {
                    ibfd.changeTypeRecursively(level, pos, this.type, fluid, 64);
                }
            } else {
                this.setFluidType(fluid);
                if (level.getBlockState(this.worldPosition).getBlock() instanceof FluidDuctConnectingBlock connectingDuct) connectingDuct.updateConnections(level, this.worldPosition, fluid);
            }
        }
    }
}
