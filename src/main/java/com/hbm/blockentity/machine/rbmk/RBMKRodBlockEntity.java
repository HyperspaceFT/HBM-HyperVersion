package com.hbm.blockentity.machine.rbmk;

import api.hbm.redstoneoverradio.IRORValueProvider;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.machine.rbmk.IRBMKFluxReceiver.NType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock.LidType;
import com.hbm.blocks.machine.rbmk.RBMKRodBlock;
import com.hbm.entity.projectile.RBMKDebris.DebrisType;
import com.hbm.handler.neutron.NeutronNodeWorld;
import com.hbm.handler.neutron.NeutronNodeWorld.StreamWorld;
import com.hbm.handler.neutron.NeutronStream;
import com.hbm.handler.neutron.RBMKNeutronHandler;
import com.hbm.handler.neutron.RBMKNeutronHandler.RBMKNeutronNode;
import com.hbm.handler.radiation.ChunkRadiationManager;
import com.hbm.inventory.menus.RBMKRodMenu;
import com.hbm.items.machine.RBMKRodItem;
import com.hbm.particle.NtmParticleTypes;
import com.hbm.particle.vanilla.NbtParticleOptions;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.protocol.game.ClientboundLevelParticlesPacket;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

import java.util.Locale;

/**
 * Original TileEntityRBMKRod: the fuel channel (rbmk_rod and the moderated rbmk_rod_mod), one rod slot. Not ported: the
 * OpenComputers callbacks and the Energy Control data (no such integrations in NEO).
 */
public class RBMKRodBlockEntity extends RBMKSlottedBaseBlockEntity implements IRBMKFluxReceiver, IRBMKLoadable, IRORValueProvider {

    // New system!!
    // Used for receiving flux (calculating outbound flux/burning rods)
    public double fluxFastRatio;
    public double fluxQuantity;
    public double lastFluxQuantity;
    public double lastFluxRatio;

    public boolean hasRod;
    public int rodColor = 0;

    // Fuel rod item data client sync
    private String fuelYield;
    private String fuelXenon;
    private String fuelHeat;

    public RBMKRodBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.RBMK_ROD.get(), pos, state, 1);
    }

    @Override
    public String getContainerName() {
        return "container.rbmkRod";
    }

    @Override
    public boolean isModerated() {
        return this.getBlockState().getBlock() instanceof RBMKRodBlock rod && rod.moderated;
    }

    @Override
    public int trackingRange() {
        return 25;
    }

    @Override
    public void receiveFlux(NeutronStream stream) {
        double fastFlux = this.fluxQuantity * this.fluxFastRatio;
        double fastFluxIn = stream.fluxQuantity * stream.fluxRatio;

        this.fluxQuantity += stream.fluxQuantity;
        fluxFastRatio = (fastFlux + fastFluxIn) / fluxQuantity;
    }

    public boolean coldEnoughForAutoloader() {
        ItemStack stack = this.slots.get(0);
        if(stack.getItem() instanceof RBMKRodItem) {
            return RBMKRodItem.getHullHeat(stack) <= 1_000;
        }
        return true;
    }
    public boolean coldEnoughForManual() {
        ItemStack stack = this.slots.get(0);
        if(stack.getItem() instanceof RBMKRodItem) {
            return RBMKRodItem.getHullHeat(stack) <= 200;
        }
        return true;
    }

    // The original's invalidate() meltdown of a hot rod (:107-114) is RBMKRodBlock.onRemove here: setRemoved also runs on chunk unload.

    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        ItemStack stack = this.slots.get(0);

        if(stack.getItem() instanceof RBMKRodItem rod) {

            // Original :123-124 reports INFO_NUCLEAR to SatelliteRayScan every 200 ticks; NEO has no SatelliteRayScan (as ZIRNOX).

            this.rodColor = rod.colorTint;

            double fluxRatioOut;
            double fluxQuantityOut;

            // Experimental flux ratio curve rods!
            // Again, nothing really uses this so its just idle code at the moment.
            if(rod.specialFluxCurve) {
                fluxRatioOut = rod.fluxRatioOut(this.fluxFastRatio, RBMKRodItem.getEnrichment(stack));
                double fluxIn = rod.fluxFromRatio(this.fluxQuantity, this.fluxFastRatio);
                fluxQuantityOut = rod.burn(this.level, stack, fluxIn);
            } else {
                NType rType = rod.rType;
                if(rType == NType.SLOW)
                    fluxRatioOut = 0;
                else
                    fluxRatioOut = 1;

                double fluxIn = fluxFromType(rod.nType);
                fluxQuantityOut = rod.burn(this.level, stack, fluxIn);
            }

            rod.updateHeat(this.level, stack, 1.0D);
            this.heat += rod.provideHeat(this.level, stack, heat, 1.0D);

            if(!this.hasLid()) {
                ChunkRadiationManager.proxy.incrementRad(this.level, this.worldPosition, (float) (this.fluxQuantity * 0.05F));
            }

            super.updateEntity();

            if(this.heat > this.maxHeat()) {

                if(RBMKDials.getMeltdownsDisabled()) {
                    spawnGasFlame();
                } else {
                    this.meltdown();
                }
                this.lastFluxRatio = 0;
                this.lastFluxQuantity = 0;
                this.fluxQuantity = 0;
                return;
            }

            if(this.heat > 10_000) this.heat = 10_000;

            //for spreading, we want the buffered flux to be 0 because we want to know exactly how much gets reflected back

            this.lastFluxQuantity = this.fluxQuantity;
            this.lastFluxRatio = this.fluxFastRatio;

            this.fluxQuantity = 0;
            this.fluxFastRatio = 0;

            spreadFlux(fluxQuantityOut, fluxRatioOut);

            hasRod = true;

            // NEO-only: the rod's custom data changes every tick; mark the chunk so a lone column is saved with its burnt-up rod.
            this.setChanged();

        } else {

            this.lastFluxRatio = 0;
            this.lastFluxQuantity = 0;
            this.fluxQuantity = 0;
            this.fluxFastRatio = 0;

            hasRod = false;

            super.updateEntity();
        }
    }

    /**
     * Original ParticleUtil.spawnGasFlame(x + 0.5, y + columnHeight + 0.5, z + 0.5, 0, 0.2, 0) with its 150 block radius. Count 0
     * keeps the directed velocity (as MachineTurbofanBlockEntity's exhaust); the scale is the original client default of 6.5.
     */
    private void spawnGasFlame() {
        if(!(this.level instanceof ServerLevel serverLevel)) return;

        double x = this.worldPosition.getX() + 0.5;
        double y = this.worldPosition.getY() + RBMKDials.getColumnHeight() + 0.5;
        double z = this.worldPosition.getZ() + 0.5;
        CompoundTag data = new CompoundTag(); data.putFloat("scale", 6.5F);
        serverLevel.getServer().getPlayerList().broadcast(null, x, y, z, 150, serverLevel.dimension(),
                new ClientboundLevelParticlesPacket(new NbtParticleOptions(NtmParticleTypes.GAS_FLAME.get(), data), true, x, y, z, 0F, 0.2F, 0F, 1F, 0));
    }

    /** Original fluxFromType (:199-211), private there. */
    public double fluxFromType(NType type) {

        double fastFlux = this.fluxQuantity * this.fluxFastRatio;
        double slowFlux = this.fluxQuantity * (1 - this.fluxFastRatio);

        switch(type) {
        case SLOW: return slowFlux + fastFlux * 0.5;
        case FAST: return fastFlux + slowFlux * 0.3;
        case ANY: return this.fluxQuantity;
        }

        return 0.0D;
    }

    public static final Direction[] fluxDirs = new Direction[] {
            Direction.NORTH,
            Direction.EAST,
            Direction.SOUTH,
            Direction.WEST
    };

    public void spreadFlux(double flux, double ratio) {

        if(flux == 0) {
            // simple way to remove the node from the cache when no flux is going into it!
            NeutronNodeWorld.removeNode(this.level, this.worldPosition);
            return;
        }

        StreamWorld streamWorld = NeutronNodeWorld.getOrAddWorld(this.level);
        RBMKNeutronNode node = (RBMKNeutronNode) streamWorld.getNode(this.worldPosition);

        if(node == null) {
            node = RBMKNeutronHandler.makeNode(streamWorld, this);
            streamWorld.addNode(node);
        }

        for(Direction dir : fluxDirs) {

            Vec3 neutronVector = new Vec3(dir.getStepX(), dir.getStepY(), dir.getStepZ());

            // Create new neutron streams
            new RBMKNeutronHandler.RBMKNeutronStream(node, neutronVector, flux, ratio);
        }
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);

        if(tag.contains("fluxFast") || tag.contains("fluxSlow")) {
            // recalculate new values to keep stable operations
            this.fluxQuantity = tag.getDouble("fluxFast") + tag.getDouble("fluxSlow");
            if(this.fluxQuantity > 0)
                this.fluxFastRatio = tag.getDouble("fluxFast") / fluxQuantity;
            else
                this.fluxFastRatio = 0;
        } else {
            this.fluxQuantity = tag.getDouble("fluxQuantity");
            this.fluxFastRatio = tag.getDouble("fluxMod");
        }
        this.hasRod = tag.getBoolean("hasRod");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);

        tag.putDouble("fluxQuantity", this.lastFluxQuantity);
        tag.putDouble("fluxMod", this.lastFluxRatio);
        tag.putBoolean("hasRod", this.hasRod);
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeDouble(this.lastFluxQuantity);
        buf.writeDouble(this.lastFluxRatio);
        buf.writeBoolean(this.hasRod);
        buf.writeInt(this.rodColor);
        if(this.hasRod) {
            // hasRod is last tick's state; the slot may have been emptied since, so the strings are empty then (the reader expects them).
            ItemStack stack = this.slots.get(0);
            if(stack.getItem() instanceof RBMKRodItem rod) {
                buf.writeUtf(RBMKRodItem.getYield(stack) + " / " + rod.yield + " (" + (RBMKRodItem.getEnrichment(stack) * 100) + "%)");
                buf.writeUtf(RBMKRodItem.getPoison(stack) + "%");
                //Heat is too long! Reduce it to 6 numbers is enough.
                // (Locale.US as in Goal24B; the original uses the default locale.)
                buf.writeUtf(String.format(Locale.US, "%.6f", RBMKRodItem.getCoreHeat(stack))
                        + " / " + String.format(Locale.US, "%.6f", RBMKRodItem.getHullHeat(stack))
                        + " / " + String.format(Locale.US, "%.2f", rod.meltingPoint));
            } else {
                buf.writeUtf("");
                buf.writeUtf("");
                buf.writeUtf("");
            }
        }
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.fluxQuantity = buf.readDouble();
        this.fluxFastRatio = buf.readDouble();
        this.hasRod = buf.readBoolean();
        this.rodColor = buf.readInt();
        if(this.hasRod) {
            fuelYield = buf.readUtf();
            fuelXenon = buf.readUtf();
            fuelHeat = buf.readUtf();
        } else {
            fuelYield = fuelXenon = fuelHeat = null;
        }
    }

    /** Original writeToNBT's diag branch (:275-279) and getDiagData (:315-325). */
    @Override
    public void getDiagData(CompoundTag nbt) {
        super.getDiagData(nbt);

        nbt.putDouble("fluxSlow", this.fluxQuantity * (1 - fluxFastRatio));
        nbt.putDouble("fluxFast", this.fluxQuantity * fluxFastRatio);
        nbt.putBoolean("hasRod", this.hasRod);

        if(fuelYield != null && fuelXenon != null && fuelHeat != null) {
            nbt.putString("f_yield", fuelYield);
            nbt.putString("f_xenon", fuelXenon);
            nbt.putString("f_heat", fuelHeat);
        }
    }

    @Override
    public void onMelt(int reduce) {

        // Read before the core is replaced (see getLid); the original reads its cached metadata at the end.
        LidType lid = this.getLid();

        boolean moderated = this.isModerated();
        int h = RBMKDials.getColumnHeight();
        reduce = Mth.clamp(reduce, 1, h);

        if(level.random.nextInt(3) == 0)
            reduce++;

        boolean corium = this.slots.get(0).getItem() instanceof RBMKRodItem;

        // Original :339-340: an rbmk_fuel_drx sets RBMKBase.digamma; DRX and the digamma meltdown are not migrated.

        // Emptied before any block changes, so neither DummyableBlock.onRemove drops the rod nor RBMKRodBlock.onRemove melts again.
        this.slots.set(0, ItemStack.EMPTY);

        if(corium) {

            DummyableBlock.safeRem = true;
            try {
                for(int i = h; i >= 0; i--) {
                    level.setBlock(this.worldPosition.above(i), NtmBlocks.CORIUM_BLOCK.get().defaultBlockState(), 3);
                }
            } finally {
                DummyableBlock.safeRem = false;
            }

            int count = 1 + level.random.nextInt(RBMKDials.getColumnHeight());

            for(int i = 0; i < count; i++) {
                spawnDebris(DebrisType.FUEL);
            }
        } else {
            this.standardMelt(reduce);
        }

        if(moderated) {

            int count = 2 + level.random.nextInt(2);

            for(int i = 0; i < count; i++) {
                spawnDebris(DebrisType.GRAPHITE);
            }
        }

        spawnDebris(DebrisType.ELEMENT);

        if(lid == LidType.STANDARD)
            spawnDebris(DebrisType.LID);
    }

    @Override
    public RBMKType getRBMKType() {
        return RBMKType.ROD;
    }

    @Override
    public RBMKColumnType getConsoleType() {
        return RBMKColumnType.FUEL;
    }

    @Override
    public CompoundTag getNBTForConsole() {
        CompoundTag data = super.getNBTForConsole();

        ItemStack stack = this.slots.get(0);
        if(stack.getItem() instanceof RBMKRodItem rod) {

            data.putDouble("enrichment", RBMKRodItem.getEnrichment(stack));
            data.putDouble("xenon", RBMKRodItem.getPoison(stack));
            data.putDouble("c_heat", RBMKRodItem.getHullHeat(stack));
            data.putDouble("c_coreHeat", RBMKRodItem.getCoreHeat(stack));
            data.putDouble("c_maxHeat", rod.meltingPoint);
        }

        return data;
    }

    @Override
    public boolean canLoad(ItemStack toLoad) {
        return !toLoad.isEmpty() && this.slots.get(0).isEmpty();
    }

    @Override
    public void load(ItemStack toLoad) {
        this.slots.set(0, toLoad.copy());
        this.setChanged();
    }

    @Override
    public boolean canUnload() {
        return !this.slots.get(0).isEmpty();
    }

    @Override
    public ItemStack provideNext() {
        return this.slots.get(0);
    }

    @Override
    public void unload() {
        this.slots.set(0, ItemStack.EMPTY);
        this.setChanged();
    }

    @Override
    public AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player) {
        return new RBMKRodMenu(containerId, inventory, this);
    }

    @Override
    public String[] getFunctionInfo() {
        return new String[] {
                PREFIX_VALUE + "columnheat",
                PREFIX_VALUE + "rodheat",
                PREFIX_VALUE + "depletion",
                PREFIX_VALUE + "xenon",
                PREFIX_VALUE + "fastflux",
                PREFIX_VALUE + "slowflux",
                PREFIX_VALUE + "flux"
        };
    }

    @Override
    public String provideRORValue(String name) {
        ItemStack stack = this.slots.get(0);
        if((PREFIX_VALUE + "columnheat").equals(name))      return "" + (int) this.heat;
        if(stack.getItem() instanceof RBMKRodItem) {
            if((PREFIX_VALUE + "rodheat").equals(name))     return "" + (int) RBMKRodItem.getHullHeat(stack);
            if((PREFIX_VALUE + "depletion").equals(name))   return "" + (int) (100 - RBMKRodItem.getEnrichment(stack) * 100);
            if((PREFIX_VALUE + "xenon").equals(name))       return "" + (int) (RBMKRodItem.getPoison(stack));
        }
        if((PREFIX_VALUE + "fastflux").equals(name))        return "" + (int) (lastFluxQuantity * lastFluxRatio);
        if((PREFIX_VALUE + "slowflux").equals(name))        return "" + (int) (lastFluxQuantity * (1 - lastFluxRatio));
        if((PREFIX_VALUE + "flux").equals(name))            return "" + ((int) (lastFluxQuantity * lastFluxRatio) + (int) (lastFluxQuantity * (1 - lastFluxRatio)));
        return null;
    }
}
