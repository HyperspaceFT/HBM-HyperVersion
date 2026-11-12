package com.hbm.blockentity.network;

import api.hbm.energymk2.IEnergyProviderMK2;
import api.hbm.energymk2.IEnergyReceiverMK2;
import api.hbm.energymk2.Nodespace;
import api.hbm.energymk2.Nodespace.PowerNode;
import api.hbm.energymk2.PowerNetMK2;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.util.EnumUtil;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Network separator (original BlockNetworkSeparator.java:99-327): a two-sided power limiter that takes power from the network on
 * its input side and passes at most its configured limit per tick to the network on its output side, never more than that network
 * asks for. The original's ports are TilePort nodes; NEO keeps the old model, so the core subscribes to the cable beyond the input
 * side and provides to the cable beyond the output side every tick.
 */
public class NetworkSeparatorBlockEntity extends LoadedBaseBlockEntity implements ITickable, IEnergyProviderMK2, IEnergyReceiverMK2, IControlReceiver {

    public static final long MAX_LIMIT = 10_000_000_000L;

    /** Inter-tick tracker for transferred power */
    protected long deltaTracker = 0;
    /** Final power per tick over the past second */
    public long[] deltaTick = new long[20];
    /** Average of the entire previous log */
    public long deltaSecond = 0;

    private long power;
    public ConnectionPriority priority = ConnectionPriority.NORMAL;
    public boolean redstone = false;
    public long configuredLimit = 1_000;
    public long actualLimit = configuredLimit;

    public NetworkSeparatorBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.NETWORK_SEPARATOR.get(), pos, state);
    }

    public Direction getFacing() {
        BlockState state = this.getBlockState();
        return state.hasProperty(DummyableBlock.FACING) ? state.getValue(DummyableBlock.FACING) : Direction.NORTH;
    }

    /** The original's getDir(false), getRotation(DOWN): the output side (BlockNetworkSeparator.java:127-133). */
    public Direction getOutDir() {
        return this.getFacing().getCounterClockWise();
    }

    /** The cable cell beyond the output side block. */
    public DirPos getOutPos() {
        Direction dir = this.getOutDir();
        return new DirPos(this.worldPosition.relative(dir, 2), dir);
    }

    /** The cable cell beyond the input side block. */
    public DirPos getInPos() {
        Direction dir = this.getOutDir().getOpposite();
        return new DirPos(this.worldPosition.relative(dir, 2), dir);
    }

    /** Only the two side faces take a cable (BlockNetworkSeparator.java:135-139). */
    @Override
    public boolean canConnect(Direction dir) {
        Direction rot = this.getOutDir();
        return dir == rot || dir == rot.getOpposite();
    }

    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        DirPos in = this.getInPos();
        DirPos out = this.getOutPos();
        this.trySubscribe(this.level, in);
        this.tryProvide(this.level, out.makeCompat(), out.getDir());

        this.actualLimit = this.configuredLimit;

        PowerNode node = Nodespace.getNode(this.level, out.makeCompat());
        if(node != null && node.net != null) this.surveyOutgoingNetwork(node.net);

        this.actualLimit = Math.max(this.actualLimit, this.power);

        long total = this.deltaTick[0];

        for(int i = 1; i < this.deltaTick.length; i++) {
            total += this.deltaTick[i];
            this.deltaTick[i - 1] = this.deltaTick[i];
        }

        this.deltaTick[19] = this.deltaTracker;
        this.deltaTracker = 0;
        this.deltaSecond = total;

        Direction dir = this.getOutDir();
        this.redstone = this.level.hasNeighborSignal(this.worldPosition)
                || this.level.hasNeighborSignal(this.worldPosition.relative(dir))
                || this.level.hasNeighborSignal(this.worldPosition.relative(dir.getOpposite()));

        this.networkPackNT(15);
    }

    @Override
    public void usePower(long power) {
        this.setPower(this.getPower() - power);
        this.deltaTracker += power;
    }

    /**
     * Lowers the limit to what the output network can take: another separator counts with its own limit, every other receiver with
     * its free space capped at its receiving speed (BlockNetworkSeparator.java:183-198). NEO's receivers are the keys of a map.
     */
    protected void surveyOutgoingNetwork(PowerNetMK2 net) {

        long demand = 0;
        for(IEnergyReceiverMK2 rec : net.receiverEntries.keySet()) {

            if(rec instanceof NetworkSeparatorBlockEntity separator) {
                demand += separator.actualLimit;
            } else {
                demand += Math.min(rec.getMaxPower() - rec.getPower(), rec.getReceiverSpeed());
            }
        }

        if(demand < this.actualLimit) this.actualLimit = demand;
    }

    @Override public long getReceiverSpeed() { return this.redstone || this.bufferMismatch() ? 0 : this.getMaxPower(); }
    @Override public long getProviderSpeed() { return this.redstone ? 0 : this.getMaxPower(); }
    @Override public long getMaxPower() { return this.actualLimit; }
    @Override public long getPower() { return this.power; }
    @Override public void setPower(long power) { this.power = power; }
    @Override public ConnectionPriority getPriority() { return this.priority; }

    /** Power reaches it only through the input side's network, not from a machine pushing into one of its blocks. */
    @Override public boolean allowDirectProvision() { return false; }

    public boolean bufferMismatch() {
        return this.configuredLimit < this.getMaxPower();
    }

    /** Within 128 squared blocks of the core's centre (BlockNetworkSeparator.java:263-266). */
    @Override
    public boolean hasPermission(Player player) {
        return player.distanceToSqr(this.worldPosition.getX() + 0.5D, this.worldPosition.getY() + 0.5D, this.worldPosition.getZ() + 0.5D) <= 128;
    }

    /** The limit is clamped to 0 to 10,000,000,000 on the server (BlockNetworkSeparator.java:268-275). */
    @Override
    public void receiveControl(CompoundTag tag) {
        if(tag.contains("limit")) this.configuredLimit = tag.getLong("limit");
        if(tag.contains("priority")) this.priority = EnumUtil.grabEnumSafely(ConnectionPriority.class, tag.getByte("priority"));
        if(this.configuredLimit < 0) this.configuredLimit = 0;
        if(this.configuredLimit > MAX_LIMIT) this.configuredLimit = MAX_LIMIT;
        this.setChanged();
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.power = tag.getLong("power");
        this.configuredLimit = tag.getLong("configuredLimit");
        this.actualLimit = tag.getLong("actualLimit");
        this.priority = EnumUtil.grabEnumSafely(ConnectionPriority.class, tag.getByte("p"));
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putLong("power", this.power);
        tag.putLong("configuredLimit", this.configuredLimit);
        tag.putLong("actualLimit", this.actualLimit);
        tag.putByte("p", (byte) this.priority.ordinal());
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeByte((byte) this.priority.ordinal());
        buf.writeBoolean(this.redstone);
        buf.writeLong(this.configuredLimit);
        buf.writeLong(this.deltaTick[19]);
        buf.writeLong(this.deltaSecond);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.priority = EnumUtil.grabEnumSafely(ConnectionPriority.class, buf.readByte());
        this.redstone = buf.readBoolean();
        this.configuredLimit = buf.readLong();
        this.deltaTick[19] = buf.readLong();
        this.deltaSecond = buf.readLong();
    }
}
