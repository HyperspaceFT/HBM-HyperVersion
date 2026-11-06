package com.hbm.blockentity.machine;

import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import com.hbm.blockentity.IConditionalInvAccess;
import com.hbm.blockentity.IFluidCopiable;
import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.handler.pollution.PollutionHandler.PollutionType;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.material.MaterialShapes;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.Mats.MaterialStack;
import com.hbm.inventory.material.NTMMaterial;
import com.hbm.inventory.menus.MachineRotaryFurnaceMenu;
import com.hbm.inventory.recipes.RotaryFurnaceRecipes;
import com.hbm.inventory.recipes.RotaryFurnaceRecipes.RotaryFurnaceRecipe;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.module.ModuleBurnTime;
import com.hbm.util.CrucibleUtil;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;

public class MachineRotaryFurnaceBlockEntity extends MachineBaseBlockEntity implements IFluidStandardTransceiverMK2, IFluidCopiable, IConditionalInvAccess {

    public static final int MAX_OUTPUT = MaterialShapes.BLOCK.q(16);

    /** Given this has no heat, the heat mod instead affects the progress per fuel. */
    public static final ModuleBurnTime BURN_MODULE = new ModuleBurnTime()
            .setCokeTimeMod(1.25)
            .setRocketTimeMod(1.5)
            .setSolidTimeMod(1.5)
            .setBalefireTimeMod(1.5)

            .setSolidHeatMod(1.5)
            .setRocketHeatMod(3)
            .setBalefireHeatMod(10);

    public final FluidTank[] tanks;
    public boolean isProgressing;
    public float progress;
    public int burnTime;
    public double burnHeat = 1D;
    public int maxBurnTime;
    public int steamUsed = 0;
    public MaterialStack output;

    public int anim;
    public int lastAnim;

    private AABB renderBox;

    public MachineRotaryFurnaceBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_ROTARY_FURNACE.get(), pos, state, 5);

        this.tanks = new FluidTank[] {
                new FluidTank(Fluids.NONE, 16_000),
                new FluidTank(Fluids.STEAM, 12_000),
                new FluidTank(Fluids.SPENTSTEAM, 120)
        };
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.machineRotaryFurnace");
    }

    /** The original rotation around DOWN: the side the furnace pours to and its fluid inlets face. */
    private Direction getRot() {
        return this.getBlockState().getValue(DummyableBlock.FACING).getCounterClockWise();
    }

    public DirPos[] getSteamPorts() {
        Direction dir = this.getBlockState().getValue(DummyableBlock.FACING);
        Direction rot = this.getRot();
        BlockPos back = this.worldPosition.relative(dir, -2);
        BlockPos outer = back.relative(rot, -2);
        BlockPos inner = back.relative(rot, -1);
        return new DirPos[] {
                new DirPos(outer.getX(), outer.getY(), outer.getZ(), dir.getOpposite()),
                new DirPos(inner.getX(), inner.getY(), inner.getZ(), dir.getOpposite())
        };
    }

    public DirPos[] getFluidPorts() {
        Direction dir = this.getBlockState().getValue(DummyableBlock.FACING);
        Direction rot = this.getRot();
        BlockPos side = this.worldPosition.relative(rot, 3);
        BlockPos front = side.relative(dir, 1);
        BlockPos back = side.relative(dir, -1);
        return new DirPos[] {
                new DirPos(front.getX(), front.getY(), front.getZ(), rot),
                new DirPos(back.getX(), back.getY(), back.getZ(), rot)
        };
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;

        Direction dir = this.getBlockState().getValue(DummyableBlock.FACING);
        Direction rot = this.getRot();

        if(!this.level.isClientSide) {

            boolean subscribe = this.level.getGameTime() % 20 == 0;

            for(DirPos pos : this.getSteamPorts()) {
                if(subscribe) this.trySubscribe(this.tanks[1].getTankType(), this.level, pos);
                if(this.tanks[2].getFill() > 0) this.tryProvide(this.tanks[2], this.level, pos);
            }

            if(subscribe && this.tanks[0].getTankType() != Fluids.NONE) {
                for(DirPos pos : this.getFluidPorts()) {
                    this.trySubscribe(this.tanks[0].getTankType(), this.level, pos);
                }
            }

            if(this.tanks[0].setType(3, this.slots)) this.setChanged();

            this.pourOutput(rot);

            RotaryFurnaceRecipe recipe = RotaryFurnaceRecipes.getRecipe(this.tanks[0].getTankType(), this.slots.get(0), this.slots.get(1), this.slots.get(2));
            boolean wasProgressing = this.isProgressing;
            this.isProgressing = false;

            if(recipe != null) {

                ItemStack fuel = this.slots.get(4);

                if(this.burnTime <= 0 && BURN_MODULE.getBurnTime(fuel) > 0) {
                    this.burnHeat = BURN_MODULE.getMod(fuel, BURN_MODULE.getModHeat());
                    this.maxBurnTime = this.burnTime = BURN_MODULE.getBurnTime(fuel) / 2;
                    this.removeItem(4, 1);
                    this.setChanged();
                }

                float processSpeed = Math.max((float) this.burnHeat, 1);
                float steamUseMult = (float) (10 * Math.log10(processSpeed) + 1);

                if(this.canProcess(recipe, steamUseMult)) {
                    this.progress += processSpeed / recipe.duration;

                    this.tanks[1].setFill((int) (this.tanks[1].getFill() - recipe.steam * steamUseMult));
                    this.steamUsed += recipe.steam * steamUseMult;
                    this.isProgressing = true;

                    if(this.progress >= 1F) {
                        this.progress -= 1F;
                        this.consumeItems(recipe);

                        if(this.output == null) {
                            this.output = recipe.output.copy();
                        } else {
                            this.output.amount += recipe.output.amount;
                        }
                    }

                    if(this.burnTime > 0) {
                        PollutionHandler.incrementPollution(this.level, this.worldPosition, PollutionType.SOOT, PollutionHandler.SOOT_PER_SECOND / 10F);
                        this.burnTime--;
                    }

                    this.setChanged();

                } else {
                    if(this.progress != 0) this.setChanged();
                    this.progress = 0;
                }

                if(this.steamUsed >= 100) {
                    int steamReturn = this.steamUsed / 100;
                    int canReturn = this.tanks[2].getMaxFill() - this.tanks[2].getFill();
                    int doesReturn = Math.min(steamReturn, canReturn);
                    this.steamUsed -= doesReturn * 100;
                    this.tanks[2].setFill(this.tanks[2].getFill() + doesReturn);
                    if(doesReturn > 0) this.setChanged();
                }

            } else {
                if(this.progress != 0) this.setChanged();
                this.progress = 0;
            }

            if(wasProgressing != this.isProgressing) this.setChanged();

            this.networkPackNT(50);

        } else {

            if(this.burnTime > 0) {
                RandomSource rand = this.level.random;
                this.level.addParticle(ParticleTypes.FLAME,
                        this.worldPosition.getX() + 0.5 + dir.getStepX() * 0.5 + rot.getStepX() + rand.nextGaussian() * 0.25,
                        this.worldPosition.getY() + 0.375,
                        this.worldPosition.getZ() + 0.5 + dir.getStepZ() * 0.5 + rot.getStepZ() + rand.nextGaussian() * 0.25,
                        0, 0, 0);
            }

            this.lastAnim = this.anim;
            if(this.isProgressing) {
                this.anim += (int) Math.max(this.burnHeat, 1);
            }
        }
    }

    /** The original's output pour; NEO has no foundry stream effect, so the stream is drawn with dust particles in the molten colour. */
    private void pourOutput(Direction rot) {
        if(this.output == null) return;

        int prev = this.output.amount;
        double x = this.worldPosition.getX() + 0.5D + rot.getStepX() * 2.875D;
        double y = this.worldPosition.getY() + 1.25D;
        double z = this.worldPosition.getZ() + 0.5D + rot.getStepZ() * 2.875D;
        Vec3[] impact = new Vec3[1];
        NTMMaterial material = this.output.material;

        this.output = CrucibleUtil.pourSingleStack(this.level, x, y, z, 6, this.output, impact);

        if(prev != this.output.amount) {
            this.setChanged();

            if(this.level instanceof ServerLevel server && impact[0] != null) {
                int color = material.moltenColor;
                double length = Math.max(0D, y - impact[0].y);
                server.sendParticles(new DustParticleOptions(new Vector3f((color >> 16 & 255) / 255F, (color >> 8 & 255) / 255F, (color & 255) / 255F), 1F),
                        x, y - length / 2D, z, 4, 0.05D, length / 4D, 0.05D, 0D);
            }
        }

        if(this.output.amount <= 0) this.output = null;
    }

    public boolean canProcess(RotaryFurnaceRecipe recipe, float steamUseMult) {

        if(this.burnTime <= 0) return false;

        if(recipe.fluid != null) {
            if(this.tanks[0].getTankType() != recipe.fluid.type) return false;
            if(this.tanks[0].getFill() < recipe.fluid.fill) return false;
        }

        if(this.tanks[1].getFill() < recipe.steam * steamUseMult) return false;
        if(this.tanks[2].getMaxFill() - this.tanks[2].getFill() < recipe.steam * steamUseMult / 100) return false;
        if(this.steamUsed > 100) return false;

        if(this.output != null) {
            if(this.output.material != recipe.output.material) return false;
            if(this.output.amount + recipe.output.amount > MAX_OUTPUT) return false;
        }

        return true;
    }

    public void consumeItems(RotaryFurnaceRecipe recipe) {

        for(AStack aStack : recipe.ingredients) {

            for(int i = 0; i < 3; i++) {
                ItemStack stack = this.slots.get(i);
                if(aStack.matchesRecipe(stack, true) && stack.getCount() >= aStack.stacksize) {
                    this.removeItem(i, aStack.stacksize);
                    break;
                }
            }
        }

        if(recipe.fluid != null) {
            this.tanks[0].setFill(this.tanks[0].getFill() - recipe.fluid.fill);
        }
    }

    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        if(slot < 3) return true;
        if(slot == 3) return stack.getItem() instanceof IItemFluidIdentifier;
        return slot == 4 && BURN_MODULE.getBurnTime(stack) > 0;
    }

    // Only the port blocks give access, one slot each (the original IConditionalInvAccess); nothing can be extracted.
    @Override public boolean canPlaceItemThroughFace(int index, ItemStack stack, Direction direction) { return false; }
    @Override public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction) { return false; }
    @Override public int[] getSlotsForFace(Direction direction) { return new int[0]; }

    @Override public boolean isItemValidForSlot(BlockPos pos, int slot, ItemStack stack) { return slot < 3 || slot == 4; }
    @Override public boolean canExtractItem(BlockPos pos, int slot, ItemStack stack, Direction direction) { return false; }

    @Override
    public int[] getAccessibleSlotsFromSide(BlockPos pos, Direction direction) {
        Direction dir = this.getBlockState().getValue(DummyableBlock.FACING);
        Direction rot = dir.getClockWise();
        BlockPos back = this.worldPosition.relative(dir, -1);

        if(direction == dir.getOpposite()) {
            // Red, yellow and green inputs on the back
            if(pos.equals(back.relative(rot, -2))) return new int[] { 0 };
            if(pos.equals(back.relative(rot, -1))) return new int[] { 1 };
            if(pos.equals(back)) return new int[] { 2 };
        }
        // Fuel on the front
        if(direction == dir && pos.equals(this.worldPosition.relative(dir, 1).relative(rot, -1))) return new int[] { 4 };

        return new int[0];
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.tanks[0].readFromNBT(tag, "t0");
        this.tanks[1].readFromNBT(tag, "t1");
        this.tanks[2].readFromNBT(tag, "t2");
        this.progress = tag.getFloat("prog");
        this.burnTime = tag.getInt("burn");
        this.burnHeat = tag.getDouble("heat");
        this.maxBurnTime = tag.getInt("maxBurn");
        this.output = null;
        if(tag.contains("outType")) {
            NTMMaterial mat = Mats.matById.get(tag.getInt("outType"));
            if(mat != null) this.output = new MaterialStack(mat, tag.getInt("outAmount"));
        }
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        this.tanks[0].writeToNBT(tag, "t0");
        this.tanks[1].writeToNBT(tag, "t1");
        this.tanks[2].writeToNBT(tag, "t2");
        tag.putFloat("prog", this.progress);
        tag.putInt("burn", this.burnTime);
        tag.putDouble("heat", this.burnHeat);
        tag.putInt("maxBurn", this.maxBurnTime);
        if(this.output != null) {
            tag.putInt("outType", this.output.material.id);
            tag.putInt("outAmount", this.output.amount);
        }
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        for(FluidTank tank : this.tanks) tank.serialize(buf);
        buf.writeBoolean(this.isProgressing);
        buf.writeFloat(this.progress);
        buf.writeInt(this.burnTime);
        buf.writeInt(this.maxBurnTime);
        buf.writeDouble(this.burnHeat);

        if(this.output != null) {
            buf.writeBoolean(true);
            buf.writeInt(this.output.material.id);
            buf.writeInt(this.output.amount);
        } else {
            buf.writeBoolean(false);
        }
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        for(FluidTank tank : this.tanks) tank.deserialize(buf);
        this.isProgressing = buf.readBoolean();
        this.progress = buf.readFloat();
        this.burnTime = buf.readInt();
        this.maxBurnTime = buf.readInt();
        this.burnHeat = buf.readDouble();

        if(buf.readBoolean()) {
            int id = buf.readInt();
            int amount = buf.readInt();
            NTMMaterial mat = Mats.matById.get(id);
            this.output = mat == null ? null : new MaterialStack(mat, amount);
        } else {
            this.output = null;
        }
    }

    @Override
    public boolean canConnect(FluidType type, Direction dir) {
        return dir != null;
    }

    @Override public FluidTank[] getAllTanks() { return this.tanks; }
    @Override public FluidTank[] getSendingTanks() { return new FluidTank[] { this.tanks[2] }; }
    @Override public FluidTank[] getReceivingTanks() { return new FluidTank[] { this.tanks[0], this.tanks[1] }; }
    @Override public FluidTank getTankToPaste() { return this.tanks[0]; }

    @Override
    public void pasteSettings(CompoundTag tag, int index, Level level, Player player, BlockPos pos) {
        IFluidCopiable.super.pasteSettings(tag, index, level, player, pos);
        this.setChanged();
    }

    public AABB getRenderBoundingBox() {
        if(this.renderBox == null) {
            BlockPos pos = this.worldPosition;
            this.renderBox = new AABB(pos.getX() - 2, pos.getY(), pos.getZ() - 2, pos.getX() + 3, pos.getY() + 5, pos.getZ() + 3);
        }
        return this.renderBox;
    }

    @Override
    public long transferFluid(FluidType type, int pressure, long amount) {
        long remainder = IFluidStandardTransceiverMK2.super.transferFluid(type, pressure, amount);
        // Pipes fill the tanks between ticks; an idle furnace would otherwise never save that fluid.
        if(remainder < amount) this.setChanged();
        return remainder;
    }

    @Override
    public void useUpFluid(FluidType type, int pressure, long amount) {
        long previous = this.getFluidAvailable(type, pressure);
        IFluidStandardTransceiverMK2.super.useUpFluid(type, pressure, amount);
        if(this.getFluidAvailable(type, pressure) != previous) this.setChanged();
    }

    @Override
    public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) {
        return new MachineRotaryFurnaceMenu(id, inventory, this);
    }
}
