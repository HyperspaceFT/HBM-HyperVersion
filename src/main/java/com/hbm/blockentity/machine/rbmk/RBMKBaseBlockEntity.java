package com.hbm.blockentity.machine.rbmk;

import api.hbm.fluidmk2.FluidNetMK2;
import api.hbm.fluidmk2.FluidNode;
import api.hbm.fluidmk2.IFluidReceiverMK2;
import com.hbm.blockentity.IOverpressurable;
import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock.LidType;
import com.hbm.entity.projectile.RBMKDebris;
import com.hbm.entity.projectile.RBMKDebris.DebrisType;
import com.hbm.handler.neutron.NeutronNodeWorld;
import com.hbm.handler.neutron.RBMKNeutronHandler.RBMKNeutronNode;
import com.hbm.network.toclient.AuxParticle;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.neoforged.neoforge.network.PacketDistributor;

import javax.annotation.Nullable;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * Base class for all RBMK components, active or passive. Handles heat and the explosion sequence
 * (original TileEntityRBMKBase). The ReaSim water/steam fields and the crane indicator are not ported yet (GOAL24 decision 5,
 * Goal 25); adding their NBT keys later stays compatible. The passive columns have no slots; the slotted columns
 * (RBMKSlottedBaseBlockEntity, Goal24C) share this parent and pass their slot count, which is why it is a MachineBaseBlockEntity.
 * @author hbm
 */
public abstract class RBMKBaseBlockEntity extends MachineBaseBlockEntity {

    public double heat;

    public RBMKBaseBlockEntity(BlockEntityType<? extends RBMKBaseBlockEntity> type, BlockPos pos, BlockState state) {
        this(type, pos, state, 0);
    }

    protected RBMKBaseBlockEntity(BlockEntityType<? extends RBMKBaseBlockEntity> type, BlockPos pos, BlockState state, int slotCount) {
        super(type, pos, state, slotCount);
    }

    /**
     * The lid of this column, kept in the core's block state. While the core is being replaced (a meltdown started from
     * RBMKRodBlock.onRemove) the level already holds the new block, so this falls back to the block entity's own state, as the
     * original's cached metadata still held the old lid.
     */
    public LidType getLid() {
        BlockState state = this.level != null ? this.level.getBlockState(this.worldPosition) : this.getBlockState();
        if(!state.hasProperty(RBMKBaseBlock.LID)) state = this.getBlockState();
        return state.hasProperty(RBMKBaseBlock.LID) ? state.getValue(RBMKBaseBlock.LID) : LidType.NONE;
    }

    public boolean hasLid() {

        if(!isLidRemovable())
            return true;

        return this.getLid() != LidType.NONE;
    }

    public boolean isLidRemovable() {
        return true;
    }

    /**
     * Called on the server after a lid was put on or taken off: updates the lid flag of this column's neutron node, as the
     * original ItemRBMKLid (:44-46, addLid) and RBMKBase.onScrew (:216-218, removeLid) do.
     */
    public void onLidChanged() {
        if(this.level == null || this.level.isClientSide) return;

        if(NeutronNodeWorld.getNode(this.level, this.worldPosition) instanceof RBMKNeutronNode node) {
            if(this.hasLid()) node.addLid();
            else node.removeLid();
        }
    }

    // Original invalidate / onChunkUnload (:237-246): the column's neutron node goes with it. Server only; client levels have no nodes.
    @Override
    public void setRemoved() {
        super.setRemoved();
        if(this.level != null && !this.level.isClientSide) NeutronNodeWorld.removeNode(this.level, this.worldPosition); // woo-fucking-hoo!!!
    }

    @Override
    public void onChunkUnloaded() {
        super.onChunkUnloaded();
        if(this.level != null && !this.level.isClientSide) NeutronNodeWorld.removeNode(this.level, this.worldPosition); // woo-fucking-hoo!!!
    }

    /**
     * Approx melting point of steel
     * Fuels often burn much hotter than this but it won't affect the column too much due to low diffusion
     * @return
     */
    public double maxHeat() {
        return 1500D;
    }

    /**
     * Around the same for every component except boilers which do not have passive cooling.
     * Requires the amount of connected neighbors to scale cooling
     * @return
     */
    public double passiveCooling(int neighbors) {
        double min = RBMKDials.getPassiveCoolingInner(); //default: 0.1D
        double max = RBMKDials.getPassiveCooling(); //default: 2.5D
        return min + (max - min) * ((4 - Mth.clamp(neighbors, 0, 4)) / 4D);
    }

    //unused
    public int trackingRange() {
        return 15;
    }

    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        moveHeat();
        this.networkPackNT(trackingRange());
    }

    // Original neighborDirs (:147-152): NORTH, EAST, SOUTH, WEST.
    public static final Direction[] neighborDirs = new Direction[] {
            Direction.NORTH,
            Direction.EAST,
            Direction.SOUTH,
            Direction.WEST
    };

    protected RBMKBaseBlockEntity[] neighborCache = new RBMKBaseBlockEntity[4];

    /**
     * Moves heat to neighboring parts, if possible, in a relatively fair manner
     */
    private void moveHeat() {

        List<RBMKBaseBlockEntity> rec = new ArrayList<>();
        rec.add(this);
        double heatTot = this.heat;

        int index = 0;
        for(Direction dir : neighborDirs) {

            if(neighborCache[index] != null && neighborCache[index].isRemoved())
                neighborCache[index] = null;

            if(neighborCache[index] == null) {
                // Only a column whose core shares this y; like the original Compat.getTileStandard this does not load chunks.
                BlockPos pos = this.worldPosition.relative(dir);
                if(this.level.isLoaded(pos) && this.level.getBlockEntity(pos) instanceof RBMKBaseBlockEntity base) {
                    neighborCache[index] = base;
                }
            }

            index++;
        }

        for(RBMKBaseBlockEntity base : neighborCache) {

            if(base != null) {
                rec.add(base);
                heatTot += base.heat;
            }
        }

        int members = rec.size();
        double stepSize = RBMKDials.getColumnHeatFlow();

        if(members > 1) {

            double targetHeat = heatTot / (double)members;

            for(RBMKBaseBlockEntity rbmk : rec) {
                double delta = targetHeat - rbmk.heat;
                rbmk.heat += delta * stepSize;
            }

            this.setChanged();
        }

        coolPassively(members - 1);
    }

    protected void coolPassively(int neighbors) {
        this.heat -= this.passiveCooling(neighbors);
        if(heat < 20) heat = 20D;
    }

    public RBMKType getRBMKType() {
        return RBMKType.OTHER;
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);

        this.heat = tag.getDouble("heat");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);

        tag.putDouble("heat", this.heat);
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeDouble(this.heat);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.heat = buf.readDouble();
    }

    /**
     * The RBMK values shown by the DODD overlay. The original dumps writeToNBT without the parent keys (diag = true, :265-311);
     * NEO writes only the RBMK keys directly, subclasses add theirs after calling super.
     */
    public void getDiagData(CompoundTag nbt) {
        nbt.putDouble("heat", this.heat);
    }

    public void onMelt(int reduce) {

        // Read before standardMelt replaces the core; the original's cached getBlockMetadata still held the old lid.
        LidType lid = this.getLid();

        standardMelt(reduce);

        if(lid == LidType.STANDARD)
            spawnDebris(DebrisType.LID);
    }

    protected void standardMelt(int reduce) {

        int h = RBMKDials.getColumnHeight();
        reduce = Mth.clamp(reduce, 1, h);

        if(level.random.nextInt(3) == 0)
            reduce++;

        // safeRem keeps the dummies from tearing down the rest of the column while it is being replaced; setBlock drops nothing.
        DummyableBlock.safeRem = true;
        try {
            for(int i = h; i >= 0; i--) {

                BlockPos pos = this.worldPosition.above(i);

                if(i <= h + 1 - reduce) {

                    if(reduce > 1 && i == h + 1 - reduce) {
                        level.setBlock(pos, NtmBlocks.PRIBRIS_BURNING.get().defaultBlockState(), 3);
                    } else {
                        level.setBlock(pos, NtmBlocks.PRIBRIS.get().defaultBlockState(), 3);
                    }

                } else {
                    level.setBlock(pos, Blocks.AIR.defaultBlockState(), 3);
                }
            }
        } finally {
            // A global flag: never leave it set, or every multiblock stops removing orphaned dummies.
            DummyableBlock.safeRem = false;
        }
    }

    protected void spawnDebris(DebrisType type) {

        RBMKDebris debris = new RBMKDebris(level, worldPosition.getX() + 0.5D, worldPosition.getY() + 4D, worldPosition.getZ() + 0.5D, type);
        double motionX = level.random.nextGaussian() * 0.25D;
        double motionZ = level.random.nextGaussian() * 0.25D;
        double motionY = 0.25D + level.random.nextDouble() * 1.25D;

        if(type == DebrisType.LID) {
            motionX *= 0.5D;
            motionY += 0.5D;
            motionZ *= 0.5D;
        }

        debris.setDeltaMovement(motionX, motionY, motionZ);
        level.addFreshEntity(debris);
    }

    /** Original meltdown (:434-573). Server side only. */
    public void meltdown() {
        if(this.level == null || this.level.isClientSide) return;

        RBMKBaseBlock.dropLids = false;
        try {
            meltConnected();
        } finally {
            // A global flag like the original's; restored even if a block replacement throws.
            RBMKBaseBlock.dropLids = true;
        }
    }

    private void meltConnected() {

        // A local set instead of the original's static one; same members, nothing kept between worlds.
        Set<RBMKBaseBlockEntity> columns = new LinkedHashSet<>();
        getFF(columns);
        // Likewise the original's static pipes set (:435).
        Set<FluidNetMK2> pipes = new LinkedHashSet<>();

        int xCoord = worldPosition.getX();
        int yCoord = worldPosition.getY();
        int zCoord = worldPosition.getZ();

        int minX = xCoord;
        int maxX = xCoord;
        int minZ = zCoord;
        int maxZ = zCoord;

        //set meltdown bounds
        for(RBMKBaseBlockEntity rbmk : columns) {

            BlockPos p = rbmk.getBlockPos();
            if(p.getX() < minX)
                minX = p.getX();
            if(p.getX() > maxX)
                maxX = p.getX();
            if(p.getZ() < minZ)
                minZ = p.getZ();
            if(p.getZ() > maxZ)
                maxZ = p.getZ();
        }

        for(RBMKBaseBlockEntity rbmk : columns) {

            BlockPos p = rbmk.getBlockPos();
            int distFromMinX = p.getX() - minX;
            int distFromMaxX = maxX - p.getX();
            int distFromMinZ = p.getZ() - minZ;
            int distFromMaxZ = maxZ - p.getZ();

            int minDist = Math.min(distFromMinX, Math.min(distFromMaxX, Math.min(distFromMinZ, distFromMaxZ)));

            // The original's boiler adds its networks inside its onMelt, before the column is replaced (TileEntityRBMKBoiler :208-215).
            if(RBMKDials.getOverpressure())
                rbmk.collectOverpressurePipes(pipes);
            rbmk.onMelt(minDist + 1);
        }

        // Original :477-498: pribris around a fuel column that melted into corium_block may become pribris_radiating. The random
        // roll comes first for every position, as the original's `rand.nextInt(3) == 0 && (...)`. The digamma branch
        // (pribris_digamma after an rbmk_fuel_drx meltdown) is not migrated.
        for(RBMKBaseBlockEntity rbmk : columns) {

            if(rbmk instanceof RBMKRodBlockEntity && level.getBlockState(rbmk.getBlockPos()).is(NtmBlocks.CORIUM_BLOCK.get())) {

                BlockPos core = rbmk.getBlockPos();

                for(int x = core.getX() - 1; x <= core.getX() + 1; x ++) {
                    for(int y = core.getY() - 1; y <= core.getY() + 1; y ++) {
                        for(int z = core.getZ() - 1; z <= core.getZ() + 1; z ++) {

                            BlockPos pos = new BlockPos(x, y, z);
                            BlockState b = level.getBlockState(pos);

                            if(level.random.nextInt(3) == 0 && (b.is(NtmBlocks.PRIBRIS.get()) || b.is(NtmBlocks.PRIBRIS_BURNING.get()))) {
                                level.setBlock(pos, NtmBlocks.PRIBRIS_RADIATING.get().defaultBlockState(), 3);
                            }
                        }
                    }
                }
            }
        }

        // Original :500-539: the overpressure branch blows up the collected pipe networks. Only the steam channels add networks
        // (RBMKBoilerBlockEntity.collectOverpressurePipes); how much steam they hold plays no part.
        if(RBMKDials.getOverpressure() && !pipes.isEmpty())
            handleOverpressure(pipes);

        int smallDim = Math.min(maxX - minX, maxZ - minZ);
        int avgX = minX + (maxX - minX) / 2;
        int avgZ = minZ + (maxZ - minZ) / 2;

        CompoundTag data = new CompoundTag();
        data.putString("type", "rbmkmush");
        data.putFloat("scale", smallDim);
        if(this.level instanceof ServerLevel serverLevel) {
            PacketDistributor.sendToPlayersNear(serverLevel, null, avgX + 0.5, yCoord + 1, avgZ + 0.5, 250, new AuxParticle(data, avgX + 0.5, yCoord + 1, avgZ + 0.5));
        }

        level.playSound(null, avgX + 0.5, yCoord + 1, avgZ + 0.5, NtmSoundEvents.RBMK_EXPLOSION.get(), SoundSource.BLOCKS, 50.0F, 1.0F);

        // The achievement (:553-558) waits for the advancement system and EntitySpear (:560-566) for the digamma path (GOAL24 decisions 5, 10).
    }

    /**
     * Adds the fluid networks this column feeds to the meltdown's overpressure set; called for every melting column right before
     * its onMelt while the overpressure dial is on. Only the steam channel has any.
     */
    protected void collectOverpressurePipes(Set<FluidNetMK2> pipes) { }

    /**
     * Original overpressure branch (:500-538): up to a fifth of the collected pipe nodes (at most 100) lose every block entity
     * block they occupy, then every subscribed receiver explodes. Ordered sets instead of the original's HashSets, so the pipes
     * that go are picked in a fixed order. The original's links also hold the UNINOS port nodes of every machine on the network
     * (TilePort); NEO's columns and machines subscribe directly, so only ducts count towards the fifth and every slot hits a duct.
     */
    private void handleOverpressure(Set<FluidNetMK2> pipes) {
        Set<FluidNode> pipeBlocks = new LinkedHashSet<>();
        Set<IFluidReceiverMK2> pipeReceivers = new LinkedHashSet<>();

        //unify all parts into single sets to prevent redundancy
        pipes.forEach(x -> {
            pipeBlocks.addAll(x.links);
            pipeReceivers.addAll(x.receiverEntries.keySet());
        });

        int count = 0;
        int max = Math.min(pipeBlocks.size() / 5, 100);
        Iterator<FluidNode> itPipes = pipeBlocks.iterator();
        Iterator<IFluidReceiverMK2> itReceivers = pipeReceivers.iterator();

        while(itPipes.hasNext() && count < max) {
            FluidNode node = itPipes.next();
            for(BlockPos pos : node.positions) {
                if(level.getBlockEntity(pos) != null) {
                    level.setBlock(pos, Blocks.AIR.defaultBlockState(), 3);
                }
            }
            count++;
        }

        while(itReceivers.hasNext()) {
            IFluidReceiverMK2 con = itReceivers.next();
            if(con instanceof BlockEntity tile) {
                BlockPos pos = tile.getBlockPos();
                if(con instanceof IOverpressurable overpressurable) {
                    overpressurable.explode(level, pos);
                } else {
                    level.setBlock(pos, Blocks.AIR.defaultBlockState(), 3);
                    // Original newExplosion(null, ..., 5F, false, false): no fire, no block damage.
                    level.explode(null, pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5, 5F, false, Level.ExplosionInteraction.NONE);
                }
            }
        }
    }

    /** Original getFF (:575-591): every column core connected to this one through the four horizontal neighbours at the same y. */
    private void getFF(Set<RBMKBaseBlockEntity> columns) {

        Deque<BlockPos> open = new ArrayDeque<>();
        open.push(this.worldPosition);

        while(!open.isEmpty()) {
            BlockPos pos = open.pop();

            if(level.isLoaded(pos) && level.getBlockEntity(pos) instanceof RBMKBaseBlockEntity rbmk && columns.add(rbmk)) {
                open.push(pos.west());
                open.push(pos.north());
                open.push(pos.south());
                open.push(pos.east());
            }
        }
    }

    public boolean isModerated() {
        return false;
    }

    public abstract RBMKColumnType getConsoleType();

    /** NEO-only: the original base returns null (:599-601) and leaves all console data to the subclasses; here the base already reports heat and maxHeat. */
    public CompoundTag getNBTForConsole() {
        CompoundTag data = new CompoundTag();
        data.putDouble("heat", this.heat);
        data.putDouble("maxHeat", this.maxHeat());
        return data;
    }

    /** Original getRenderBoundingBox (:607-610): up to y + 17, enough for the lid of any column height. */
    public AABB getRenderBoundingBox() {
        return new AABB(worldPosition.getX(), worldPosition.getY(), worldPosition.getZ(), worldPosition.getX() + 1, worldPosition.getY() + 17, worldPosition.getZ() + 1);
    }

    /**
     * The fluid connections of a column with ports (original getPortsNoLoader / getPortsCloseLoader / getPortsClassicLoader,
     * :612-644, picked every tick as TileEntityRBMKBoiler.updateEntity :71-72 does): always above the top segment; with an
     * rbmk_loader two blocks below the core ("classic") also below the core and around the loader; with one directly below
     * ("close") around the loader; otherwise below the core. A connection is the block next to a port, facing away from it
     * (TilePort.PortDef.make). The columns subscribe and provide there directly instead of through port nodes.
     */
    protected List<DirPos> getPortConnections() {

        int h = RBMKDials.getColumnHeight();
        BlockPos core = this.worldPosition;
        List<DirPos> cons = new ArrayList<>();

        cons.add(new DirPos(core.above(h + 1), Direction.UP));

        BlockPos loader = null;
        if(level.getBlockState(core.below(2)).is(NtmBlocks.RBMK_LOADER.get())) {
            cons.add(new DirPos(core.below(), Direction.DOWN));
            loader = core.below(2);
        } else if(level.getBlockState(core.below()).is(NtmBlocks.RBMK_LOADER.get())) {
            loader = core.below();
        } else {
            cons.add(new DirPos(core.below(), Direction.DOWN));
        }

        if(loader != null) {
            for(Direction dir : Direction.values()) {
                BlockPos pos = loader.relative(dir);
                // NEO-only: the close loader's upward connection is this column's own core (original getPortsCloseLoader
                // :623-632), where no node can exist; the skip only drops that dead connection.
                if(pos.getX() == core.getX() && pos.getZ() == core.getZ() && pos.getY() >= core.getY() && pos.getY() <= core.getY() + h) continue;
                cons.add(new DirPos(pos, dir));
            }
        }

        return cons;
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable(this.getBlockState().getBlock().getDescriptionId());
    }

    // No slots: nothing is exposed to hoppers or pipes (the parent's default face slot {0} would be out of range).
    @Override
    public int[] getSlotsForFace(Direction direction) {
        return new int[0];
    }

    // The passive columns have no GUI; the slotted columns of Goal24C bring their menus.
    @Override
    public @Nullable AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player) {
        return null;
    }
}
