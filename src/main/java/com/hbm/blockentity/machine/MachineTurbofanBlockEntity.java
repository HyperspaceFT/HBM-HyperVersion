package com.hbm.blockentity.machine;

import api.hbm.energymk2.IBatteryItem;
import api.hbm.energymk2.IEnergyProviderMK2;
import api.hbm.energymk2.PowerNetMK2;
import api.hbm.fluidmk2.FluidNetMK2;
import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import com.hbm.blockentity.IFluidCopiable;
import com.hbm.blockentity.IUpgradeInfoProvider;
import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.handler.pollution.PollutionHandler.PollutionType;
import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.UpgradeManagerNT;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.fluid.trait.FT_Combustible;
import com.hbm.inventory.fluid.trait.FT_Combustible.FuelGrade;
import com.hbm.inventory.fluid.trait.FT_Polluting;
import com.hbm.inventory.menus.MachineTurbofanMenu;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.items.machine.MachineUpgradeItem;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.lib.Library;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toclient.AuxParticle;
import com.hbm.particle.NtmParticleTypes;
import com.hbm.particle.vanilla.NbtParticleOptions;
import com.hbm.registry.NtmDamageTypes;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.sound.AudioWrapper;
import com.hbm.uninos.NodeNet;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.game.ClientboundLevelParticlesPacket;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.network.PacketDistributor;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Standard turbofan; fuel consumption and danger do not depend on the energy buffer's remaining space. */
public class MachineTurbofanBlockEntity extends MachineBaseBlockEntity implements IEnergyProviderMK2, IFluidStandardTransceiverMK2, IFluidCopiable, IUpgradeInfoProvider {

    public static final long MAX_POWER = 1_000_000L;
    public static final int TANK_CAPACITY = 24_000;
    public static final int SMOKE_CAPACITY = 150;
    public static final int SLOT_FLUID_IN = 0;
    public static final int SLOT_FLUID_OUT = 1;
    public static final int SLOT_AFTERBURNER = 2;
    public static final int SLOT_BATTERY = 3;
    public static final int SLOT_IDENTIFIER = 4;
    private static final int[] AUTOMATION_SLOTS = {};

    public long power;
    public final FluidTank tank = new FluidTank(Fluids.KEROSENE, TANK_CAPACITY);
    public final FluidTank blood = new FluidTank(Fluids.BLOOD, TANK_CAPACITY);
    public final FluidTank smoke = new FluidTank(Fluids.SMOKE, SMOKE_CAPACITY);
    public final FluidTank smokeLeaded = new FluidTank(Fluids.SMOKE_LEADED, SMOKE_CAPACITY);
    public final FluidTank smokePoison = new FluidTank(Fluids.SMOKE_POISON, SMOKE_CAPACITY);
    public int afterburner;
    public boolean wasOn;
    public boolean showBlood;
    public boolean redstonePowered;
    public int output;
    public int consumption;
    public float spin;
    public float lastSpin;
    public int momentum;
    public final UpgradeManagerNT upgradeManager = new UpgradeManagerNT(this);
    private FluidType subscribedType;
    private AudioWrapper audio;

    public MachineTurbofanBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_TURBOFAN.get(), pos, state, 5);
    }
    @Override protected Component getDefaultName() { return Component.translatable("container.machine_turbofan"); }
    public long getPowerScaled(long pixels) { return this.power * pixels / MAX_POWER; }

    /** Forge 1.7.10's getRotation(UP) maps NORTH to EAST, matching this horizontal rotation. */
    public static Direction getIntakeDirection(Direction facing) { return facing.getClockWise(); }
    public static DirPos[] getPortProxies(BlockPos core, Direction facing) {
        Direction intake = getIntakeDirection(facing);
        return new DirPos[] {
                new DirPos(core.relative(facing), facing),
                new DirPos(core.relative(facing).relative(intake.getOpposite()), facing),
                new DirPos(core.relative(facing.getOpposite()), facing.getOpposite()),
                new DirPos(core.relative(facing.getOpposite()).relative(intake.getOpposite()), facing.getOpposite()) };
    }
    public DirPos[] getConPos() {
        DirPos[] proxies = getPortProxies(this.worldPosition, this.getBlockState().getValue(DummyableBlock.FACING));
        DirPos[] connections = new DirPos[proxies.length];
        for(int i = 0; i < proxies.length; i++) connections[i] = new DirPos(proxies[i].makeCompat().relative(proxies[i].getDir()), proxies[i].getDir());
        return connections;
    }
    public static long getBurnValue(FluidType type) {
        FT_Combustible fuel = type.getTrait(FT_Combustible.class);
        return fuel != null && fuel.getGrade() == FuelGrade.AERO ? fuel.getCombustionEnergy() / 1_000L : 0L;
    }
    public static int getGeneratedPower(long burnValue, int amount, int afterburner) {
        return (int)(burnValue * amount * (1 + Math.min(afterburner / 3D, 4D)));
    }

    @Override public void updateEntity() {
        if(this.level == null) return;
        if(this.level.isClientSide) { this.updateAnimation(); this.updateLocalPlayer(); return; }
        long previousPower = this.power;
        FluidType previousType = this.tank.getTankType();
        int previousFill = this.tank.getFill();
        if(this.subscribedType != null && this.subscribedType != previousType) this.removeFluidSubscriptions();
        for(DirPos pos : this.getConPos()) {
            if(!this.level.hasChunkAt(pos.makeCompat())) continue;
            this.trySubscribe(previousType, this.level, pos);
            this.tryProvide(this.blood, this.level, pos);
            this.tryProvide(this.level, pos.makeCompat(), pos.getDir());
        }
        this.subscribedType = previousType;
        // Retyping precedes item loading in the original, so a new identifier can accept its container this tick.
        boolean changed = this.tank.setType(SLOT_IDENTIFIER, this.slots);
        if(changed) this.removeFluidSubscriptions();
        changed |= this.tank.loadTank(this.level, SLOT_FLUID_IN, SLOT_FLUID_OUT, this.slots);
        this.upgradeManager.checkSlots(this.slots, SLOT_AFTERBURNER, SLOT_AFTERBURNER);
        this.afterburner = this.upgradeManager.getLevel(UpgradeType.AFTERBURN);
        this.redstonePowered = false;
        for(DirPos pos : this.getConPos()) {
            if(this.level.hasChunkAt(pos.makeCompat()) && this.level.hasNeighborSignal(pos.makeCompat())) { this.redstonePowered = true; break; }
        }
        this.generate(this.redstonePowered);
        // Keep the full generated buffer available to charging, then discard only the remaining overflow.
        this.power = Library.chargeItemsFromTE(this.slots, SLOT_BATTERY, this.power, this.power);
        this.applyEntityEffects();
        this.power = Math.min(this.power, MAX_POWER);
        if(changed || this.power != previousPower || this.tank.getFill() != previousFill || this.tank.getTankType() != previousType) this.setChanged();
        this.networkPackNT(150);
    }
    public void generate(boolean redstone) {
        this.wasOn = false;
        this.output = 0;
        this.consumption = 0;
        if(this.level == null || this.level.isClientSide || redstone) return;
        int amount = Math.min(1 + this.afterburner, this.tank.getFill());
        if(amount <= 0) return;
        this.wasOn = true;
        this.tank.setFill(this.tank.getFill() - amount);
        this.output = getGeneratedPower(getBurnValue(this.tank.getTankType()), amount, this.afterburner);
        this.power += this.output;
        this.consumption = amount;
        // The original polluting base ignores amount; an mB multiplier would change this machine's emissions.
        if(this.level.getGameTime() % 20 == 0) this.polluteFuel(this.tank.getTankType());
        this.setChanged();
    }
    public void polluteFuel(FluidType type) {
        if(this.level == null || this.level.isClientSide) return;
        FT_Polluting trait = type.getTrait(FT_Polluting.class);
        if(trait == null) return;
        for(Map.Entry<PollutionType, Float> entry : trait.burnMap.entrySet()) {
            FluidTank buffer = entry.getKey() == PollutionType.SOOT ? this.smoke : entry.getKey() == PollutionType.HEAVYMETAL ? this.smokeLeaded : this.smokePoison;
            int produced = (int)Math.ceil(entry.getValue() * 100);
            int total = buffer.getFill() + produced;
            buffer.setFill(Math.min(total, SMOKE_CAPACITY));
            if(total > SMOKE_CAPACITY) {
                PollutionHandler.incrementPollution(this.level, this.worldPosition, entry.getKey(), (total - SMOKE_CAPACITY) / 100F);
                if(this.level.random.nextInt(3) == 0) this.level.playSound(null, this.worldPosition, SoundEvents.FIRE_EXTINGUISH, SoundSource.BLOCKS, 0.1F, 1.5F);
            }
            if(produced != 0) this.setChanged();
        }
    }

    private static AABB getRegion(BlockPos core, Direction facing, double start, double end) {
        Direction intake = getIntakeDirection(facing);
        Direction side = intake.getClockWise();
        double x1 = core.getX() + 0.5 + intake.getStepX() * start - side.getStepX() * 1.5;
        double z1 = core.getZ() + 0.5 + intake.getStepZ() * start - side.getStepZ() * 1.5;
        double x2 = core.getX() + 0.5 + intake.getStepX() * end + side.getStepX() * 1.5;
        double z2 = core.getZ() + 0.5 + intake.getStepZ() * end + side.getStepZ() * 1.5;
        return new AABB(Math.min(x1, x2), core.getY(), Math.min(z1, z2), Math.max(x1, x2), core.getY() + 3, Math.max(z1, z2));
    }
    public static AABB getExhaustBox(BlockPos core, Direction facing) { return getRegion(core, facing, -3.5D, -19.5D); }
    public static AABB getIntakeBox(BlockPos core, Direction facing) { return getRegion(core, facing, 3.5D, 8.5D); }
    public static AABB getBlenderBox(BlockPos core, Direction facing) { return getRegion(core, facing, 3.5D, 3.75D); }
    public void applyEntityEffects() {
        if(this.level == null || this.level.isClientSide || !this.wasOn || this.consumption <= 0 || getBurnValue(this.tank.getTankType()) <= 0) return;
        Direction facing = this.getBlockState().getValue(DummyableBlock.FACING);
        Direction intake = getIntakeDirection(facing);
        if(this.afterburner > 0 && this.level instanceof ServerLevel serverLevel) this.emitExhaust(serverLevel, intake);
        for(Entity entity : this.level.getEntitiesOfClass(Entity.class, getExhaustBox(this.worldPosition, facing), entity -> true)) {
            if(this.afterburner > 0) { entity.igniteForSeconds(5F); entity.hurt(entity.damageSources().onFire(), 5F); }
            pushEntity(entity, intake);
        }
        for(Entity entity : this.level.getEntitiesOfClass(Entity.class, getIntakeBox(this.worldPosition, facing), entity -> true)) pushEntity(entity, intake);
        for(Entity entity : this.level.getEntitiesOfClass(Entity.class, getBlenderBox(this.worldPosition, facing), entity -> true)) {
            entity.hurt(entity.damageSources().source(NtmDamageTypes.TURBOFAN), 1000F);
            // The modern hook resets fall distance and applies the multiplier on the next move, like setInWeb.
            entity.makeStuckInBlock(Blocks.COBWEB.defaultBlockState(), new Vec3(0.25D, 0.05F, 0.25D));
            // Preserve the post-hit alive check, without requiring hurt's return or a pre-hit alive flag.
            if(!entity.isAlive() && entity instanceof LivingEntity) {
                if(this.level instanceof ServerLevel serverLevel) {
                    CompoundTag data = new CompoundTag();
                    data.putString("type", "giblets"); data.putInt("ent", entity.getId()); data.putInt("cDiv", 5);
                    double y = entity.getY() + entity.getBbHeight() * 0.5;
                    PacketDistributor.sendToPlayersNear(serverLevel, null, entity.getX(), y, entity.getZ(), 150, new AuxParticle(data, entity.getX(), y, entity.getZ()));
                    serverLevel.playSound(null, entity.getX(), entity.getY(), entity.getZ(), SoundEvents.ZOMBIE_BREAK_WOODEN_DOOR, SoundSource.BLOCKS, 2F, 0.95F + this.level.random.nextFloat() * 0.2F);
                }
                this.blood.setFill(Math.min(TANK_CAPACITY, this.blood.getFill() + 50));
                this.showBlood = true;
                this.setChanged();
            }
        }
    }
    private static void pushEntity(Entity entity, Direction intake) {
        // The original's server-side motion change never reaches players; updateLocalPlayer pushes the local player on the client instead.
        if(entity instanceof Player) return;
        entity.setDeltaMovement(entity.getDeltaMovement().add(-intake.getStepX() * 0.2D, 0D, -intake.getStepZ() * 0.2D));
    }
    private void emitExhaust(ServerLevel serverLevel, Direction intake) {
        for(int i = 0; i < 2; i++) {
            double speed = 2D + this.level.random.nextDouble() * 3D;
            double deviation = this.level.random.nextGaussian() * 0.2D;
            double x = this.worldPosition.getX() + 0.5 - intake.getStepX() * (3 - i);
            double y = this.worldPosition.getY() + 1.5;
            double z = this.worldPosition.getZ() + 0.5 - intake.getStepZ() * (3 - i);
            CompoundTag data = new CompoundTag(); data.putFloat("scale", 8F);
            // Count zero carries directed velocity; the shared count-one helper randomizes it.
            serverLevel.getServer().getPlayerList().broadcast(null, x, y, z, 150, serverLevel.dimension(),
                    new ClientboundLevelParticlesPacket(new NbtParticleOptions(NtmParticleTypes.GAS_FLAME.get(), data), true, x, y, z,
                            (float)(-intake.getStepX() * speed + deviation), 0F, (float)(-intake.getStepZ() * speed + deviation), 1F, 0));
        }
    }

    private void updateAnimation() {
        this.lastSpin = this.spin;
        this.momentum = Mth.clamp(this.momentum + (this.wasOn ? 1 : -1), 0, 100);
        this.spin += this.momentum / 2;
        if(this.spin >= 360F) { this.spin -= 360F; this.lastSpin -= 360F; }
        if(this.momentum > 0) {
            if(this.audio == null) { this.audio = this.createAudioLoop(); if(this.audio != null) this.audio.startSound(); }
            else if(!this.audio.isPlaying()) this.audio = this.rebootAudio(this.audio);
            if(this.audio != null) {
                this.audio.keepAlive();
                this.audio.updateVolume(this.getVolume(this.momentum / 50F));
                this.audio.updatePitch(this.momentum / 200F + 0.5F + this.afterburner * 0.16F);
            }
        } else this.stopAudio();
    }
    private void updateLocalPlayer() {
        if(!this.wasOn || this.consumption <= 0 || this.redstonePowered || getBurnValue(this.tank.getTankType()) <= 0) return;
        Player player = NuclearTechMod.proxy.me();
        if(player == null || player.level() != this.level || player.isCreative()) return;
        Direction facing = this.getBlockState().getValue(DummyableBlock.FACING);
        Direction intake = getIntakeDirection(facing);
        AABB box = player.getBoundingBox();
        // The server's motion changes never reach the player, and the velocity packet carries no stuck multiplier; like the original, repeat the push and the web for the local non-creative player on the client.
        if(box.intersects(getExhaustBox(this.worldPosition, facing))) {
            player.setDeltaMovement(player.getDeltaMovement().add(-intake.getStepX() * 0.2D, 0D, -intake.getStepZ() * 0.2D));
        }
        if(box.intersects(getIntakeBox(this.worldPosition, facing))) {
            player.setDeltaMovement(player.getDeltaMovement().add(-intake.getStepX() * 0.2D, 0D, -intake.getStepZ() * 0.2D));
        }
        if(box.intersects(getBlenderBox(this.worldPosition, facing))) {
            player.makeStuckInBlock(Blocks.COBWEB.defaultBlockState(), new Vec3(0.25D, 0.05F, 0.25D));
        }
    }
    @Override public AudioWrapper createAudioLoop() {
        return this.level != null && this.level.isClientSide ? AudioWrapper.getLoopedSound(NtmSoundEvents.TURBOFAN_OPERATE.get(), SoundSource.BLOCKS, this, 1F, 50F, 1F, 20) : null;
    }
    private void stopAudio() { if(this.audio != null) { this.audio.stopSound(); this.audio = null; } }
    public AABB getRenderBoundingBox() { return new AABB(this.worldPosition).inflate(4D); }
    private void removeFluidSubscriptions() {
        if(this.level == null || this.level.isClientSide) return;
        for(NodeNet net : new ArrayList<>(UniNodespace.activeNodeNets)) {
            if(net instanceof FluidNetMK2 fluidNet) { fluidNet.removeReceiver(this); fluidNet.removeProvider(this); }
        }
        this.subscribedType = null;
    }
    private void removeNetworkSubscriptions() {
        if(this.level == null || this.level.isClientSide) return;
        this.removeFluidSubscriptions();
        for(NodeNet net : new ArrayList<>(UniNodespace.activeNodeNets)) if(net instanceof PowerNetMK2 powerNet) powerNet.removeProvider(this);
    }
    @Override public void onChunkUnloaded() { this.removeNetworkSubscriptions(); this.stopAudio(); super.onChunkUnloaded(); }
    @Override public void setRemoved() { this.removeNetworkSubscriptions(); this.stopAudio(); super.setRemoved(); }
    @Override public boolean canConnect(Direction direction) { return direction.getAxis() == this.getBlockState().getValue(DummyableBlock.FACING).getAxis(); }
    @Override public boolean canConnect(FluidType type, Direction direction) { return this.canConnect(direction); }
    @Override public long getPower() { return this.power; }
    @Override public long getMaxPower() { return MAX_POWER; }
    @Override public void setPower(long power) {
        long bounded = Math.max(0L, Math.min(MAX_POWER, power));
        if(this.power != bounded) { this.power = bounded; this.setChanged(); }
    }
    @Override public FluidTank[] getReceivingTanks() { return new FluidTank[] { this.tank }; }
    // The original's smoke module is never updated by this machine; only blood has an output port.
    @Override public FluidTank[] getSendingTanks() { return new FluidTank[] { this.blood }; }
    @Override public FluidTank[] getAllTanks() { return new FluidTank[] { this.tank, this.blood, this.smoke, this.smokeLeaded, this.smokePoison }; }
    @Override public long transferFluid(FluidType type, int pressure, long amount) {
        long remainder = IFluidStandardTransceiverMK2.super.transferFluid(type, pressure, amount);
        if(remainder < amount) this.setChanged();
        return remainder;
    }
    @Override public void useUpFluid(FluidType type, int pressure, long amount) {
        long previous = this.getFluidAvailable(type, pressure);
        IFluidStandardTransceiverMK2.super.useUpFluid(type, pressure, amount);
        if(this.getFluidAvailable(type, pressure) != previous) this.setChanged();
    }
    @Override public FluidTank getTankToPaste() { return this.tank; }
    @Override public void pasteSettings(CompoundTag tag, int index, Level level, Player player, BlockPos pos) {
        if(tag == null || player == null || level != this.level || level.isClientSide || !this.worldPosition.equals(pos)
                || player.level() != level || !this.stillValid(player) || !tag.contains("FluidID", Tag.TAG_INT_ARRAY)) return;
        int[] ids = tag.getIntArray("FluidID");
        if(index < 0 || index >= ids.length) return;
        FluidType type = Fluids.fromID(ids[index]);
        if(type == null || type.getID() != ids[index]) return;
        if(type != this.tank.getTankType()) { this.removeFluidSubscriptions(); this.tank.setTankType(type); this.setChanged(); }
    }
    @Override public boolean canPlaceItem(int slot, ItemStack stack) {
        return switch(slot) {
            case SLOT_FLUID_IN -> FluidContainerRegistry.getFluidContent(stack, this.tank.getTankType()) > 0;
            case SLOT_AFTERBURNER -> stack.getItem() instanceof MachineUpgradeItem upgrade && upgrade.type == UpgradeType.AFTERBURN && upgrade.tier >= 1 && upgrade.tier <= 3;
            case SLOT_BATTERY -> stack.getItem() instanceof IBatteryItem;
            case SLOT_IDENTIFIER -> stack.getItem() instanceof IItemFluidIdentifier;
            default -> false;
        };
    }
    @Override public int[] getSlotsForFace(Direction direction) { return AUTOMATION_SLOTS; }
    @Override public boolean canPlaceItemThroughFace(int slot, ItemStack stack, Direction direction) { return false; }
    @Override public boolean canTakeItemThroughFace(int slot, ItemStack stack, Direction direction) { return false; }
    @Override public ItemStack removeItemNoUpdate(int slot) {
        ItemStack removed = super.removeItemNoUpdate(slot);
        if(!removed.isEmpty()) this.setChanged();
        return removed;
    }
    @Override public void clearContent() {
        boolean changed = !this.isEmpty();
        super.clearContent();
        if(changed) this.setChanged();
    }
    @Override public boolean canProvideInfo(UpgradeType type, int level, TooltipFlag flag) { return type == UpgradeType.AFTERBURN; }
    @Override public void provideInfo(UpgradeType type, int level, List<Component> components, TooltipFlag flag) {
        components.add(IUpgradeInfoProvider.getStandardLabel(NtmBlocks.MACHINE_TURBOFAN.get()));
        if(type == UpgradeType.AFTERBURN) {
            components.add(Component.translatable(KEY_EFFICIENCY, "+" + (int)(level * 100 * (1 + Math.min(level / 3D, 4D))) + "%").withStyle(ChatFormatting.GREEN));
            components.add(Component.translatable(KEY_CONSUMPTION, "+" + level * 100 + "%").withStyle(ChatFormatting.RED));
        }
    }
    @Override public HashMap<UpgradeType, Integer> getValidUpgrades() {
        HashMap<UpgradeType, Integer> upgrades = new HashMap<>(); upgrades.put(UpgradeType.AFTERBURN, 3); return upgrades;
    }

    private static void readTank(CompoundTag tag, FluidTank tank, String name, int capacity, FluidType fixedType) {
        if(!tag.contains(name + "_type")) return;
        CompoundTag bounded = tag.copy();
        bounded.putInt(name + "_max", capacity); bounded.putShort(name + "_p", (short)0);
        if(fixedType != null) bounded.putInt(name + "_type", fixedType.getID());
        tank.readFromNBT(bounded, name);
    }
    @Override protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.power = Math.max(0L, Math.min(MAX_POWER, tag.getLong("powerTime")));
        readTank(tag, this.tank, "fuel", TANK_CAPACITY, null);
        readTank(tag, this.blood, "blood", TANK_CAPACITY, Fluids.BLOOD);
        readTank(tag, this.smoke, "smoke0", SMOKE_CAPACITY, Fluids.SMOKE);
        readTank(tag, this.smokeLeaded, "smoke1", SMOKE_CAPACITY, Fluids.SMOKE_LEADED);
        readTank(tag, this.smokePoison, "smoke2", SMOKE_CAPACITY, Fluids.SMOKE_POISON);
        this.showBlood = tag.getBoolean("showBlood");
        this.wasOn = false; this.redstonePowered = false; this.afterburner = 0; this.output = 0; this.consumption = 0;
    }
    @Override protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putLong("powerTime", this.power); tag.putBoolean("showBlood", this.showBlood);
        this.tank.writeToNBT(tag, "fuel"); this.blood.writeToNBT(tag, "blood");
        this.smoke.writeToNBT(tag, "smoke0"); this.smokeLeaded.writeToNBT(tag, "smoke1"); this.smokePoison.writeToNBT(tag, "smoke2");
    }
    @Override public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeLong(this.power); buf.writeByte(this.afterburner); buf.writeBoolean(this.wasOn); buf.writeBoolean(this.showBlood);
        buf.writeBoolean(this.redstonePowered); buf.writeInt(this.output); buf.writeInt(this.consumption);
        for(FluidTank tank : this.getAllTanks()) tank.serialize(buf);
    }
    @Override public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.power = buf.readLong(); this.afterburner = buf.readByte(); this.wasOn = buf.readBoolean(); this.showBlood = buf.readBoolean();
        this.redstonePowered = buf.readBoolean(); this.output = buf.readInt(); this.consumption = buf.readInt();
        for(FluidTank tank : this.getAllTanks()) tank.deserialize(buf);
    }
    @Override public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) { return new MachineTurbofanMenu(id, inventory, this); }
}
