package com.hbm.blockentity.network;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blocks.network.RadioTorchRWBaseBlock;
import com.hbm.interfaces.IControlReceiver;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.Connection;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.game.ClientGamePacketListener;
import net.minecraft.network.protocol.game.ClientboundBlockEntityDataPacket;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;

public class RadioTorchBaseBlockEntity extends LoadedBaseBlockEntity implements ITickable, IControlReceiver {

    /** Longest channel name; the screens cap their text boxes at it and the server cuts longer control input. Original GUIScreenRadioTorch.java:24 */
    public static final int MAX_CHAN_LENGTH = 15;
    /** Longest custom mapping value, the screen's text box limit (original GUIScreenRadioTorch.java:76) */
    public static final int MAX_MAPPING_LENGTH = 32;

    /** channel we're broadcasting on/listening to */
    public String channel = "";
    /** previous redstone state for input/output, needed for state change detection */
    public int lastState = 0;
    /** last update tick, needed for receivers listening for changes */
    public long lastUpdate;
    /** switches state change mode to tick-based polling */
    public boolean polling = false;
    /** switches redstone passthrough to custom signal mapping */
    public boolean customMap = false;
    /** custom mapping */
    public String[] mapping = new String[16];

    public RadioTorchBaseBlockEntity(BlockEntityType<? extends RadioTorchBaseBlockEntity> type, BlockPos pos, BlockState state) {
        super(type, pos, state);
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;

        if(!this.level.isClientSide) {

            this.networkPackNT(50);
        }
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);

        this.polling = tag.getBoolean("p");
        this.customMap = tag.getBoolean("m");
        this.lastState = tag.getInt("l");
        this.lastUpdate = tag.getLong("u");
        this.channel = tag.getString("c");
        for(int i = 0; i < 16; i++) this.mapping[i] = tag.getString("m" + i);
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);

        tag.putBoolean("p", polling);
        tag.putBoolean("m", customMap);
        tag.putInt("l", lastState);
        tag.putLong("u", lastUpdate);
        if(channel != null) tag.putString("c", channel);
        for(int i = 0; i < 16; i++) if(mapping[i] != null) tag.putString("m" + i, mapping[i]);
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {

        buf.writeBoolean(this.polling);
        buf.writeBoolean(this.customMap);
        buf.writeUtf(this.channel);
        // all 16 entries, an unset one as an empty string, so deserialize always reads as many as were written (the original
        // BufferUtil.writeString writes a length of -1 for null, BufferUtil.java:20-28)
        for(int i = 0; i < 16; i++) buf.writeUtf(this.mapping[i] == null ? "" : this.mapping[i]);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {

        this.polling = buf.readBoolean();
        this.customMap = buf.readBoolean();
        this.channel = buf.readUtf();
        for(int i = 0; i < 16; i++) this.mapping[i] = buf.readUtf();
    }

    @Override
    public CompoundTag getUpdateTag(HolderLookup.Provider registries) {
        CompoundTag tag = super.getUpdateTag(registries);
        tag.putByte("l", (byte) this.lastState);
        return tag;
    }

    /**
     * Only the redstone state, as the original onDataPacket (TileEntityRadioTorchBase.java:92-99). NeoForge's default would load the
     * whole block entity from this sparse tag and reset the channel, modes and mapping that networkPackNT syncs.
     */
    @Override
    public void handleUpdateTag(CompoundTag tag, HolderLookup.Provider registries) {
        this.lastState = tag.getByte("l");
    }

    @Override
    public void onDataPacket(Connection net, ClientboundBlockEntityDataPacket pkt, HolderLookup.Provider registries) {
        this.handleUpdateTag(pkt.getTag(), registries);
    }

    /** Sends the changed lastState to clients and mirrors "lastState > 0" into the LIT block state that picks the on/off model. */
    protected void onStateChanged() {
        if(this.level == null) return;
        BlockState state = this.getBlockState();
        boolean lit = this.lastState > 0;
        if(state.hasProperty(RadioTorchRWBaseBlock.LIT) && state.getValue(RadioTorchRWBaseBlock.LIT) != lit) {
            this.level.setBlock(this.worldPosition, state.setValue(RadioTorchRWBaseBlock.LIT, lit), Block.UPDATE_CLIENTS);
        } else {
            this.level.sendBlockUpdated(this.worldPosition, state, state, Block.UPDATE_CLIENTS);
        }
    }

    @Override
    public boolean hasPermission(Player player) {
        // original TileEntityRadioTorchBase.java:101-104: closer than 16 blocks to the block centre
        return player.distanceToSqr(worldPosition.getX() + 0.5D, worldPosition.getY() + 0.5D, worldPosition.getZ() + 0.5D) < 16D * 16D;
    }

    @Override
    public void receiveControl(CompoundTag data) {
        if(data.contains("p")) this.polling = data.getBoolean("p");
        if(data.contains("m")) this.customMap = data.getBoolean("m");
        // the client text boxes stop at these lengths; longer input only comes from a modified client and is cut here
        if(data.contains("c")) this.channel = truncate(data.getString("c"), MAX_CHAN_LENGTH);
        for(int i = 0; i < 16; i++) if(data.contains("m" + i)) this.mapping[i] = truncate(data.getString("m" + i), MAX_MAPPING_LENGTH);

        this.setChanged();
    }

    public static String truncate(String text, int maxLength) {
        return text.length() > maxLength ? text.substring(0, maxLength) : text;
    }

    @Override
    public Packet<ClientGamePacketListener> getUpdatePacket() {
        return ClientboundBlockEntityDataPacket.create(this);
    }
}
