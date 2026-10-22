package com.hbm.blockentity.machine.rbmk;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock;
import com.hbm.extprop.HbmPlayerAttachments;
import com.hbm.handler.HbmKeybinds.EnumKeybind;
import com.hbm.items.machine.RBMKRodItem;
import com.hbm.main.NuclearTechMod;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

import java.util.List;

/**
 * Original TileEntityCraneConsole: the RBMK crane console core. Linked to a column with the rbmk_tool, it measures the free room
 * around the crane girders above the reactor; a player standing in front of the console steers the crane with the crane keys and
 * lowers the lift to load or unload one item through IRBMKLoadable. The column below the lift shows the crane indicator on the
 * RBMK console. The OpenComputers callbacks (:391-480) are not ported.
 */
public class RBMKCraneConsoleBlockEntity extends LoadedBaseBlockEntity implements ITickable {

    public int centerX;
    public int centerY;
    public int centerZ;

    public int spanF;
    public int spanB;
    public int spanL;
    public int spanR;

    public int height;

    public boolean setUpCrane = false;

    public int craneRotationOffset = 0;

    public double lastTiltFront = 0;
    public double lastTiltLeft = 0;
    public double tiltFront = 0;
    public double tiltLeft = 0;

    public double lastPosFront = 0;
    public double lastPosLeft = 0;
    public double posFront = 0;
    public double posLeft = 0;
    public double syncFront = 0;
    public double syncLeft = 0;
    private static final double speed = 0.05D;

    private boolean goesDown = false;
    public double lastProgress = 1D;
    public double progress = 1D;
    public double syncProgress = 1D;

    private ItemStack loadedItem = ItemStack.EMPTY;
    private boolean hasLoaded = false;
    public double loadedHeat;
    public double loadedEnrichment;

    // Upstream-shared: nothing sets turnProgress (the original deserialize leaves it at 0), so the client snaps to the synced values.
    private int turnProgress;

    public RBMKCraneConsoleBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.RBMK_CRANE_CONSOLE.get(), pos, state);
    }

    /** Original updateEntity (:72-194); runs on both sides. */
    @Override
    public void updateEntity() {
        if(this.level == null) return;

        if(this.level.isClientSide) {
            lastTiltFront = tiltFront;
            lastTiltLeft = tiltLeft;

            lastPosFront = posFront;
            lastPosLeft = posLeft;
            lastProgress = progress;

            if(this.turnProgress > 0) {
                this.posFront = this.posFront + ((this.syncFront - this.posFront) / (double) this.turnProgress);
                this.posLeft = this.posLeft + ((this.syncLeft - this.posLeft) / (double) this.turnProgress);
                this.progress = this.progress + ((this.syncProgress - this.progress) / (double) this.turnProgress);
                --this.turnProgress;
            } else {
                this.posFront = this.syncFront;
                this.posLeft = this.syncLeft;
                this.progress = this.syncProgress;
            }
        }

        if(!this.level.isClientSide) {
            RBMKBaseBlockEntity aboveColumn = this.getColumnAtPos();
            if(aboveColumn != null) aboveColumn.craneIndicator = 10;

            if(goesDown) {

                if(progress > 0) {
                    progress -= 0.04D;
                } else {
                    progress = 0;
                    goesDown = false;

                    if(aboveColumn instanceof IRBMKLoadable column && this.canTargetInteract(column)) {
                        if(!this.loadedItem.isEmpty()) {
                            column.load(this.loadedItem);
                            this.loadedItem = ItemStack.EMPTY;
                        } else {
                            this.loadedItem = column.provideNext();
                            column.unload();
                        }

                        this.setChanged();
                    }

                }
            } else if(progress != 1) {

                progress += 0.04D;

                if(progress > 1D) {
                    progress = 1D;
                }
            }
        }

        // Original :132-145: the operator's box, three blocks wide around the core, two high, and reaching two blocks from the core's
        // centre towards the facing (the placer's side).
        Direction dir = this.getBlockState().getValue(DummyableBlock.FACING);
        Direction side = dir.getClockWise();
        double minX = this.worldPosition.getX() + 0.5 - side.getStepX() * 1.5;
        double maxX = this.worldPosition.getX() + 0.5 + side.getStepX() * 1.5 + dir.getStepX() * 2;
        double minZ = this.worldPosition.getZ() + 0.5 - side.getStepZ() * 1.5;
        double maxZ = this.worldPosition.getZ() + 0.5 + side.getStepZ() * 1.5 + dir.getStepZ() * 2;

        List<Player> players = this.level.getEntitiesOfClass(Player.class, new AABB(
                Math.min(minX, maxX),
                this.worldPosition.getY(),
                Math.min(minZ, maxZ),
                Math.max(minX, maxX),
                this.worldPosition.getY() + 2,
                Math.max(minZ, maxZ)));
        tiltFront = 0;
        tiltLeft = 0;

        if(!players.isEmpty() && !isCraneLoading()) {
            // As the original, only the first player found steers the crane.
            Player player = players.get(0);
            boolean up = isKeyPressed(player, EnumKeybind.CRANE_UP);
            boolean down = isKeyPressed(player, EnumKeybind.CRANE_DOWN);
            boolean left = isKeyPressed(player, EnumKeybind.CRANE_LEFT);
            boolean right = isKeyPressed(player, EnumKeybind.CRANE_RIGHT);

            int front = 0;
            if(up && !down) front = 1;
            if(!up && down) front = -1;
            int sideways = 0;
            if(left && !right) sideways = 1;
            if(!left && right) sideways = -1;

            this.moveCrane(front, sideways);

            if(isKeyPressed(player, EnumKeybind.CRANE_LOAD)) {
                this.startLoad();
            }
        }

        posFront = Mth.clamp(posFront, -spanB, spanF);
        posLeft = Mth.clamp(posLeft, -spanR, spanL);

        if(!this.level.isClientSide) {

            if(!loadedItem.isEmpty() && loadedItem.getItem() instanceof RBMKRodItem) {
                this.loadedHeat = RBMKRodItem.getHullHeat(loadedItem);
                this.loadedEnrichment = RBMKRodItem.getEnrichment(loadedItem);
            } else {
                this.loadedHeat = 0;
                this.loadedEnrichment = 0;
            }

            this.networkPackNT(250);
        }
    }

    /**
     * The movement part of the original key handling (:157-172), public so the GameTests can drive it. front and left are -1, 0 or 1;
     * a non-zero value tilts the joystick by 30 degrees on both sides and moves the crane by one step on the server. The caller checks
     * isCraneLoading and the tick clamps the position afterwards, as the original.
     */
    public void moveCrane(int front, int left) {
        double prevFront = this.posFront;
        double prevLeft = this.posLeft;
        boolean server = this.level != null && !this.level.isClientSide;

        if(front != 0) {
            tiltFront = 30 * front;
            if(server) posFront += speed * front;
        }
        if(left != 0) {
            tiltLeft = 30 * left;
            if(server) posLeft += speed * left;
        }

        // NEO addition: 1.7.10 saved every tile entity of a chunk; here the saved position only persists when marked.
        if(this.posFront != prevFront || this.posLeft != prevLeft) this.setChanged();
    }

    /**
     * The key state the original reads from HbmPlayerProps (:151-155). The server keeps it in the player attachment (KeybindReceiver ->
     * HbmKeybindsServer). On the client the original's props held the local player's own keys (HbmKeybinds.java:205); NEO's synced
     * attachment is replaced by every server sync, so the client asks the proxy instead, as the original's ClientProxy.getIsKeyPressed
     * (:1973-1987) does. Other players' keys are unknown to a client and read as released, as in the original.
     */
    private static boolean isKeyPressed(Player player, EnumKeybind key) {
        if(!player.level().isClientSide) return HbmPlayerAttachments.getData(player).getKeyPressed(key);
        return player == NuclearTechMod.proxy.me() && NuclearTechMod.proxy.getIsKeyPressed(key);
    }

    /** The load key of the original (:174-176): the lift goes down on the next ticks. */
    public void startLoad() {
        this.goesDown = true;
    }

    /** Original :196-202: the server knows the held item, the client only the synced flag. */
    public boolean hasItemLoaded() {

        if(this.level == null || !this.level.isClientSide)
            return !this.loadedItem.isEmpty();
        else
            return this.hasLoaded;
    }

    /** NEO-only accessor for the GameTests: the item the lift holds, EMPTY when none (and always on the client). */
    public ItemStack getLoadedItem() {
        return this.loadedItem;
    }

    public boolean isCraneLoading() {
        return this.progress != 1D;
    }

    public boolean isAboveValidTarget() {
        return getLoadableAtPos() != null;
    }

    public boolean canTargetInteract(IRBMKLoadable column) {

        if(column == null)
            return false;

        if(this.hasItemLoaded()) {
            return column.canLoad(loadedItem);
        } else {
            return column.canUnload();
        }
    }

    /** Original :224-245: the column core under the lift, one block below the crane's base height. */
    public RBMKBaseBlockEntity getColumnAtPos() {
        // NEO-defensive: an unlinked crane points at y = -1, outside the 1.7.10 world (always air there) but inside the 1.21 build
        // height; and like the RBMK console (getColumnEntity) this never loads a chunk: an unloaded position reads as no column.
        if(this.level == null || !this.setUpCrane) return null;

        Direction dir = this.getBlockState().getValue(DummyableBlock.FACING);
        Direction left = dir.getCounterClockWise();

        int x = (int)Math.floor(this.centerX - dir.getStepX() * this.posFront - left.getStepX() * this.posLeft + 0.5D);
        int y = this.centerY - 1;
        int z = (int)Math.floor(this.centerZ - dir.getStepZ() * this.posFront - left.getStepZ() * this.posLeft + 0.5D);

        BlockPos pos = new BlockPos(x, y, z);
        if(!this.level.isLoaded(pos)) return null;
        Block b = this.level.getBlockState(pos).getBlock();

        if(b instanceof RBMKBaseBlock rbmk) {

            BlockPos core = rbmk.findCore(this.level, pos);
            // NEO-defensive: the original casts the block entity at the core without a type check.
            if(core != null && this.level.getBlockEntity(core) instanceof RBMKBaseBlockEntity column) {
                return column;
            }
        }

        return null;
    }

    public IRBMKLoadable getLoadableAtPos() {
        RBMKBaseBlockEntity column = this.getColumnAtPos();
        if(column instanceof IRBMKLoadable loadable) return loadable;
        return null;
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeBoolean(this.setUpCrane);

        if(this.setUpCrane) { //no need to send any of this if there's NO FUCKING CRANE THERE
            buf.writeInt(this.craneRotationOffset);
            buf.writeInt(this.centerX);
            buf.writeInt(this.centerY);
            buf.writeInt(this.centerZ);
            buf.writeInt(this.spanF);
            buf.writeInt(this.spanB);
            buf.writeInt(this.spanL);
            buf.writeInt(this.spanR);
            buf.writeInt(this.height);
            buf.writeDouble(this.posFront);
            buf.writeDouble(this.posLeft);
            buf.writeDouble(this.progress);
            buf.writeBoolean(this.hasItemLoaded());
            buf.writeDouble(this.loadedHeat);
            buf.writeDouble(this.loadedEnrichment);
        }
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.setUpCrane = buf.readBoolean();
        if(this.setUpCrane) {
            this.craneRotationOffset = buf.readInt();
            this.centerX = buf.readInt();
            this.centerY = buf.readInt();
            this.centerZ = buf.readInt();
            this.spanF = buf.readInt();
            this.spanB = buf.readInt();
            this.spanL = buf.readInt();
            this.spanR = buf.readInt();
            this.height = buf.readInt();
            this.syncFront = buf.readDouble();
            this.syncLeft = buf.readDouble();
            this.syncProgress = buf.readDouble();
            this.hasLoaded = buf.readBoolean();
            this.loadedHeat = buf.readDouble();
            this.loadedEnrichment = buf.readDouble();
        }
    }

    /**
     * Original :298-319: centres the crane over the given column core, at the top of the columns, and measures the free span in
     * each direction along the girder level six blocks higher (forward is away from the console).
     */
    public void setTarget(int x, int y, int z) {
        this.centerX = x;
        this.centerY = y + RBMKDials.getColumnHeight() + 1;
        this.centerZ = z;

        int girderY = centerY + 6;

        Direction dir = this.getBlockState().getValue(DummyableBlock.FACING).getOpposite();
        this.spanF = this.findRoomExtent(x, girderY, z, dir, 16);
        dir = dir.getClockWise();
        this.spanR = this.findRoomExtent(x, girderY, z, dir, 16);
        dir = dir.getClockWise();
        this.spanB = this.findRoomExtent(x, girderY, z, dir, 16);
        dir = dir.getClockWise();
        this.spanL = this.findRoomExtent(x, girderY, z, dir, 16);

        this.height = 7;

        this.setUpCrane = true;

        this.setChanged();
    }

    private int findRoomExtent(int x, int y, int z, Direction dir, int max) {
        for(int i = 1; i < max; i++) {
            if(!this.level.isEmptyBlock(new BlockPos(x + dir.getStepX() * i, y, z + dir.getStepZ() * i))) {
                return i - 1;
            }
        }

        return max;
    }

    /** Original :331-333: turns the drawn crane by a quarter; the movement axes stay the same. */
    public void cycleCraneRotation() {
        this.craneRotationOffset = (this.craneRotationOffset + 90) % 360;
        this.setChanged();
    }

    // Original NBT keys (:335-378); the lift progress and goesDown are not saved.
    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);

        this.setUpCrane = tag.getBoolean("crane");
        this.craneRotationOffset = tag.getInt("craneRotationOffset");
        this.centerX = tag.getInt("centerX");
        this.centerY = tag.getInt("centerY");
        this.centerZ = tag.getInt("centerZ");
        this.spanF = tag.getInt("spanF");
        this.spanB = tag.getInt("spanB");
        this.spanL = tag.getInt("spanL");
        this.spanR = tag.getInt("spanR");
        this.height = tag.getInt("height");
        this.posFront = tag.getDouble("posFront");
        this.posLeft = tag.getDouble("posLeft");

        this.loadedItem = tag.contains("held") ? ItemStack.parseOptional(registries, tag.getCompound("held")) : ItemStack.EMPTY;
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);

        tag.putBoolean("crane", setUpCrane);
        tag.putInt("craneRotationOffset", craneRotationOffset);
        tag.putInt("centerX", centerX);
        tag.putInt("centerY", centerY);
        tag.putInt("centerZ", centerZ);
        tag.putInt("spanF", spanF);
        tag.putInt("spanB", spanB);
        tag.putInt("spanL", spanL);
        tag.putInt("spanR", spanR);
        tag.putInt("height", height);
        tag.putDouble("posFront", posFront);
        tag.putDouble("posLeft", posLeft);

        if(!this.loadedItem.isEmpty()) {
            tag.put("held", this.loadedItem.save(registries));
        }
    }

    /** Original getRenderBoundingBox (:380-383): the crane can be anywhere above the reactor. */
    public AABB getRenderBoundingBox() {
        return AABB.INFINITE;
    }
}
