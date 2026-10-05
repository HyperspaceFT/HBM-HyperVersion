package com.hbm.blockentity.machine.storage;

import api.hbm.energymk2.IEnergyReceiverMK2.ConnectionPriority;
import api.hbm.fluidmk2.FluidNode;
import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import com.hbm.blockentity.*;
import com.hbm.blocks.DummyableBlock;
import com.hbm.explosion.vanillant.ExplosionVNT;
import com.hbm.extprop.HbmPlayerAttachments;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.NtmTags;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.fluid.trait.FT_Corrosive;
import com.hbm.inventory.fluid.trait.FT_Flammable;
import com.hbm.inventory.fluid.trait.FluidTraitSimple.FT_Gaseous;
import com.hbm.inventory.fluid.trait.FluidTraitSimple.FT_Gaseous_ART;
import com.hbm.inventory.fluid.trait.FluidTraitSimple.FT_Liquid;
import com.hbm.inventory.menus.MachineFluidTankMenu;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.lib.Library;
import com.hbm.lib.ModAttachments;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.Direction.Axis;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.world.MenuProvider;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Explosion;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;

public class MachineFluidTankBlockEntity extends MachineBaseBlockEntity implements IFluidStandardTransceiverMK2, IPersistentNBT, IOverpressurable, MenuProvider, IRepairable, IFluidCopiable, IControlReceiver {

    protected FluidNode node;
    protected FluidType lastType;

    public FluidTank tank;
    public short mode = 0;
    public static final short MODES = 4;
    public boolean hasExploded = false;
    public boolean onFire = false;
    public byte lastRedstone = 0;
    public Explosion lastExplosion = null;

    public int age = 0;

    public MachineFluidTankBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.FLUID_TANK.get(), pos, state, 6);

        this.tank = new FluidTank(Fluids.NONE, 256000);
    }

    @Override public Component getDefaultName() { return Component.translatable("container.fluidtank"); }

    // As in the original: nothing moves while the tank is broken or in a mode that does not send or receive
    @Override public long getReceiverSpeed(FluidType type, int pressure) { return this.hasExploded ? 0 : (mode == 0 || mode == 1) ? Math.max(500, (tank.getMaxFill() - tank.getFill()) / 100) : 0; }
    @Override public long getProviderSpeed(FluidType type, int pressure) { return this.hasExploded ? 0 : (mode == 1 || mode == 2) ? Math.max(500, tank.getFill() / 100) : 0; }

    public byte getComparatorPower() {
        if(tank.getFill() == 0) return 0;
        double frac = (double) tank.getFill() / (double) tank.getMaxFill() * 15D;
        return (byte) (Math.clamp(frac + 1, 0, 15));
    }

    @Override
    public void updateEntity() {
        if(level != null && !level.isClientSide) {
            if(!hasExploded) {
                age++;

                if(age >= 20) {
                    age = 0;
                    this.setChanged();
                }

                // In buffer mode, acts like a pipe block, providing fluid to its own node
                // otherwise, it is a regular providing/receiving machine, blocking further propagation
                if(mode == 1) {
                    if(this.node == null || this.node.expired || tank.getTankType() != lastType) {
                        // A node of the previous fluid type must not stay behind in the old network (as the barrel)
                        if(this.node != null) {
                            this.destroyNode();
                        }

                        FluidNode existing = (FluidNode) UniNodespace.getNode(level, getBlockPos(), tank.getTankType().getNetworkProvider());
                        if(existing == null || existing.expired) {
                            this.node = this.createNode(tank.getTankType());
                            UniNodespace.createNode(level, this.node);
                        } else {
                            this.node = existing;
                        }
                        lastType = tank.getTankType();
                    }

                    if(node != null && node.hasValidNet()) {
                        node.net.addProvider(this);
                        node.net.addReceiver(this);
                    }
                } else {
                    this.destroyNode();

                    for(DirPos pos : getConPos()) {
                        FluidNode dirNode = (FluidNode) UniNodespace.getNode(level, pos.makeCompat(), tank.getTankType().getNetworkProvider());

                        if(mode == 2) {
                            tryProvide(tank, level, pos.makeCompat(), pos.getDir());
                        } else {
                            if(dirNode != null && dirNode.hasValidNet()) dirNode.net.removeProvider(this);
                        }

                        if(mode == 0) {
                            if(dirNode != null && dirNode.hasValidNet()) dirNode.net.addReceiver(this);
                        } else {
                            if(dirNode != null && dirNode.hasValidNet()) dirNode.net.removeReceiver(this);
                        }
                    }
                }

                if(tank.loadTank(level, 2, 3, slots)) this.setChanged();
                if(tank.setType(0, 1, slots)) this.setChanged();
            } else {
                this.destroyNode();
            }

            byte comp = this.getComparatorPower(); //comparator shit
            if (comp != this.lastRedstone) {
                this.setChanged();
                // A comparator at a connection point reads the tank block behind it, so notify that block's neighbours
                // (the original notified the block at the connection point directly)
                for(DirPos pos : this.getConPos()) this.level.updateNeighbourForOutputSignal(pos.makeCompat().relative(pos.getDir().getOpposite()), this.getBlockState().getBlock());
            }
            this.lastRedstone = comp;

            if(tank.getFill() > 0) {
                if(tank.getTankType().isAntimatter()) {
                    new ExplosionVNT(level, getBlockPos().getX() + 0.5, getBlockPos().getY() + 1.5, getBlockPos().getZ() + 0.5, 5F).makeAmat().setBlockAllocator(null).setBlockProcessor(null).explode();
                    this.explode();
                    this.tank.setFill(0);
                }

                if(tank.getTankType().hasTrait(FT_Corrosive.class) && tank.getTankType().getTrait(FT_Corrosive.class).isHighlyCorrosive()) {
                    this.explode();
                }

                if(this.hasExploded) {

                    int leaking;
                    if(tank.getTankType().isAntimatter()) {
                        leaking = tank.getFill();
                    } else if(tank.getTankType().hasTrait(FT_Gaseous.class) || tank.getTankType().hasTrait(FT_Gaseous_ART.class)) {
                        leaking = Math.min(tank.getFill(), tank.getMaxFill() / 100);
                    } else {
                        leaking = Math.min(tank.getFill(), tank.getMaxFill() / 10000);
                    }

                    updateLeak(leaking);
                }
            }

            if(tank.unloadTank(level, 4, 5, slots)) this.setChanged();

            this.networkPackNT(150);
        }

        if(level != null) {
            Direction dir = this.getBlockState().getValue(DummyableBlock.FACING);
            Direction rot = dir.getClockWise(Axis.Y);
            BlockPos pos = this.getBlockPos();
            int x = pos.getX();
            int y = pos.getY();
            int z = pos.getZ();
            List<Player> players = level.getEntitiesOfClass(Player.class, new AABB(x, y, z, x + 1, y + 2.875, z + 1).move(dir.getStepX() * 0.5 - rot.getStepX() * 2.25, 0, dir.getStepZ() * 0.5 - rot.getStepZ() * 2.25));

            for(Player player : players) {
                HbmPlayerAttachments props = HbmPlayerAttachments.getData(player);
                props.isOnLadder = true;
                player.setData(ModAttachments.PLAYER_ATTACHMENT.get(), props);
            }
        }
    }

    @Override
    public void setRemoved() {
        super.setRemoved();
        this.destroyNode();
    }

    @Override
    public void onChunkUnloaded() {
        super.onChunkUnloaded();
        this.destroyNode();
    }

    /** Removes this tank's buffer-mode node, whichever fluid type it was made for (as the barrel). */
    private void destroyNode() {
        if(this.level == null || this.level.isClientSide) return;
        if(this.node != null) {
            UniNodespace.destroyNode(this.level, this.node);
            this.node = null;
            this.lastType = null;
        }
    }

    protected FluidNode createNode(FluidType type) {
        DirPos[] conPos = getConPos();

        HashSet<BlockPos> posSet = new HashSet<>();
        posSet.add(new BlockPos(this.getBlockPos()));
        for(DirPos pos : conPos) {
            Direction dir = pos.getDir();
            posSet.add(new BlockPos(pos.getX() - dir.getStepX(), pos.getY() - dir.getStepY(), pos.getZ() - dir.getStepZ()));
        }

        return new FluidNode(type.getNetworkProvider(), posSet.toArray(new BlockPos[posSet.size()])).setConnections(conPos);
    }


    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeShort(mode);
        buf.writeBoolean(hasExploded);
        tank.serialize(buf);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        mode = buf.readShort();
        hasExploded = buf.readBoolean();
        tank.deserialize(buf);
    }

    /** called when the tank breaks due to hazardous materials or external force, can be used to quickly void part of the tank or spawn a mushroom cloud */
    public void explode() {
        this.hasExploded = true;
        this.onFire = tank.getTankType().hasTrait(FT_Flammable.class);
        this.setChanged();
    }

    /** called every tick post explosion, used for leaking fluid and spawning particles */
    public void updateLeak(int amount) {
        if(!hasExploded) return;
        if(amount <= 0) return;

        this.tank.getTankType().onFluidRelease(this, tank, amount);
        this.tank.setFill(Math.max(0, this.tank.getFill() - amount));
    }

    @Override
    public void explode(Level level, BlockPos pos) {
        if(this.hasExploded) return;
        this.onFire = tank.getTankType().hasTrait(FT_Flammable.class);
        this.hasExploded = true;
        this.setChanged();
    }

    protected DirPos[] getConPos() {

        int x = this.getBlockPos().getX();
        int y = this.getBlockPos().getY();
        int z = this.getBlockPos().getZ();

        return new DirPos[] {
                new DirPos(x + 2, y, z - 1, Library.POS_X),
                new DirPos(x + 2, y, z + 1, Library.POS_X),
                new DirPos(x - 2, y, z - 1, Library.NEG_X),
                new DirPos(x - 2, y, z + 1, Library.NEG_X),
                new DirPos(x - 1, y, z + 2, Library.POS_Z),
                new DirPos(x + 1, y, z + 2, Library.POS_Z),
                new DirPos(x - 1, y, z - 2, Library.NEG_Z),
                new DirPos(x + 1, y, z - 2, Library.NEG_Z)
        };
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);

        mode = tag.getShort("Mode");
        tank.readFromNBT(tag, "Tank");
        hasExploded = tag.getBoolean("Exploded");
        onFire = tag.getBoolean("OnFire");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);

        tag.putShort("Mode", mode);
        tank.writeToNBT(tag, "Tank");
        tag.putBoolean("Exploded", hasExploded);
        tag.putBoolean("OnFire", onFire);
    }

    @Override
    public long transferFluid(FluidType type, int pressure, long fluid) {
        long toTransfer = Math.min(getDemand(type, pressure), fluid);
        tank.setFill(tank.getFill() + (int) toTransfer);
        if(toTransfer > 0) this.setChanged();
        return fluid - toTransfer;
    }

    @Override
    public void useUpFluid(FluidType type, int pressure, long amount) {
        IFluidStandardTransceiverMK2.super.useUpFluid(type, pressure, amount);
        // Network and direct provision drain the tank between this tank's own ticks (as the barrel)
        if(amount > 0) this.setChanged();
    }

    @Override
    public long getDemand(FluidType type, int pressure) {
        if(this.hasExploded) return 0;
        if(this.mode == 2 || this.mode == 3) return 0;
        if(tank.getPressure() != pressure) return 0;
        return type == tank.getTankType() ? tank.getMaxFill() - tank.getFill() : 0;
    }

    @Override
    public FluidTank[] getAllTanks() {
        return new FluidTank[] { tank };
    }

    @Override
    public void writeNBT(CompoundTag savedTag) {
        if(this.tank.getFill() == 0 && !this.hasExploded) return;
        CompoundTag tag = new CompoundTag();
        this.tank.writeToNBT(tag, "Tank");
        tag.putShort("Mode", mode);
        tag.putBoolean("HasExploded", hasExploded);
        tag.putBoolean("OnFire", onFire);
        savedTag.put(NBT_PERSISTENT_KEY, tag);
    }

    @Override
    public void readNBT(CompoundTag savedTag) {
        CompoundTag tag = savedTag.getCompound(NBT_PERSISTENT_KEY);
        this.tank.readFromNBT(tag, "Tank");
        this.mode = tag.getShort("Mode");
        this.hasExploded = tag.getBoolean("HasExploded");
        this.onFire = tag.getBoolean("OnFire");
    }

    @Override public boolean canConnect(FluidType fluid, Direction dir) { return true; }

    @Override
    public FluidTank[] getSendingTanks() {
        if(this.hasExploded) return FluidTank.EMPTY_ARRAY;
        return (mode == 1 || mode == 2) ? new FluidTank[] {tank} : FluidTank.EMPTY_ARRAY;
    }

    @Override
    public FluidTank[] getReceivingTanks() {
        if(this.hasExploded) return FluidTank.EMPTY_ARRAY;
        return (mode == 0 || mode == 1) ? new FluidTank[] {tank} : FluidTank.EMPTY_ARRAY;
    }

    @Override
    public ConnectionPriority getFluidPriority() {
        return mode == 1 ? ConnectionPriority.LOW : ConnectionPriority.NORMAL;
    }

    @Override
    public int[] getFluidIDToCopy() {
        return new int[] {tank.getTankType().getID()};
    }

    @Override
    public FluidTank getTankToPaste() {
        return tank;
    }

    @Override
    public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) {
        return new MachineFluidTankMenu(id, inventory, this);
    }

    @Override
    public boolean isDamaged() {
        return this.hasExploded;
    }

    private final List<AStack> repair = new ArrayList<>();

    @Override
    public List<AStack> getRepairMaterials() {
        if(!repair.isEmpty()) return repair;
        // Original: 6 steel plates (ore dictionary)
        repair.add(new TagStack(NtmTags.Items.PLATES_STEEL, 6));
        return repair;
    }

    @Override
    public void repair() {
        this.hasExploded = false;
        this.setChanged();
    }

    @Override
    public void tryExtinguish(Level level, BlockPos pos, EnumExtinguishType type) {
        if(!this.hasExploded || !this.onFire) return;

        if(type == EnumExtinguishType.WATER) {
            if(tank.getTankType().hasTrait(FT_Liquid.class)) { // extinguishing oil with water is a terrible idea!
                level.explode(null, this.getBlockPos().getX() + 0.5, this.getBlockPos().getY() + 1.5, this.getBlockPos().getZ() + 0.5, 5F, Level.ExplosionInteraction.TNT);
            } else {
                this.onFire = false;
                this.setChanged();
                return;
            }
        }

        if(type == EnumExtinguishType.FOAM || type == EnumExtinguishType.CO2) {
            this.onFire = false;
            this.setChanged();
        }
    }

    // Slot rules as the barrel (same layout: 0/1 identifier, 2/3 containers into the tank, 4/5 containers out of it).
    // The extra blocks carry no inventory, so automation only reaches the core.
    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        return switch(slot) {
            case 0, 1 -> stack.getItem() instanceof IItemFluidIdentifier;
            case 2 -> {
                int content = FluidContainerRegistry.getFluidContent(stack, this.tank.getTankType());
                yield content > 0 && content <= this.tank.getMaxFill();
            }
            case 4 -> {
                ItemStack full = FluidContainerRegistry.getFullContainer(stack, this.tank.getTankType());
                yield !full.isEmpty() && FluidContainerRegistry.getFluidContent(full, this.tank.getTankType()) <= this.tank.getMaxFill();
            }
            default -> true;
        };
    }

    @Override
    public boolean canTakeItemThroughFace(int slot, ItemStack stack, Direction direction) {
        return switch(slot) {
            case 1, 3, 5 -> true;
            default -> !this.canPlaceItem(slot, stack);
        };
    }

    @Override
    public int[] getSlotsForFace(Direction direction) {
        return switch(direction.get3DDataValue()) {
            case 0 -> new int[] {3, 5};
            case 1 -> new int[] {2};
            default -> new int[] {4};
        };
    }

    @Override public boolean hasPermission(Player player) { return this.stillValid(player); }

    @Override
    public void receiveControl(CompoundTag tag) {
        if(tag.contains("Mode")) {
            mode = (short) ((mode + 1) % MODES);
            this.setChanged();
        }
    }
}
