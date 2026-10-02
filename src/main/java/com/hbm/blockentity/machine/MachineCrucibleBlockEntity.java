package com.hbm.blockentity.machine;

import api.hbm.tile.IHeatSource;
import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.inventory.material.MaterialShapes;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.NTMMaterial;
import com.hbm.inventory.menus.MachineCrucibleMenu;
import com.hbm.inventory.recipes.CopperCastingRecipes;
import com.hbm.inventory.recipes.CrucibleRecipe;
import com.hbm.inventory.recipes.CrucibleRecipes;
import com.hbm.items.CopperScrapsItem;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.CollisionContext;

import java.util.ArrayList;
import java.util.List;

/**
 * Crucible adapted from upstream TileEntityCrucible: a recipe stack for the selected alloy and a waste stack
 * for everything else. The recipe stack pours from the front spout, the waste stack from the rear spout.
 */
public class MachineCrucibleBlockEntity extends MachineBaseBlockEntity implements IControlReceiver {
    public static final int MAX_HEAT = 100_000;
    public static final int PROCESS_TIME = 20_000;
    /** Capacity of each stack (upstream recipeZCapacity and wasteZCapacity). */
    public static final int CAPACITY = MaterialShapes.BLOCK.q(16);
    public static final String NO_RECIPE = "null";
    /** Upper bound for synced stack entries; each stack holds at most one entry per registered material. */
    private static final int MAX_SYNC_ENTRIES = 64;
    public int heat;
    public int progress;
    public String recipe = NO_RECIPE;
    public final List<Mats.MaterialStack> recipeStack = new ArrayList<>();
    public final List<Mats.MaterialStack> wasteStack = new ArrayList<>();
    private boolean stacksChanged;

    public MachineCrucibleBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_CRUCIBLE.get(), pos, state, 9);
    }

    @Override protected Component getDefaultName() { return Component.translatable("container.machine_crucible"); }
    @Override public int getMaxStackSize() { return 1; }

    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;
        int oldHeat = this.heat, oldProgress = this.progress;
        this.tryPullHeat();
        if(this.level.getGameTime() % 5 == 0) this.collectItems();

        if(!this.trySmelt()) this.progress = 0;
        this.tryRecipe();

        if(!this.wasteStack.isEmpty()) this.pour(this.getWasteDirection(), this.wasteStack);
        if(!this.recipeStack.isEmpty()) this.pour(this.getRecipeDirection(), this.getCastableRecipeMaterials());

        if(this.recipeStack.removeIf(stack -> stack.amount <= 0)) this.stacksChanged = true;
        if(this.wasteStack.removeIf(stack -> stack.amount <= 0)) this.stacksChanged = true;

        if(this.stacksChanged || oldHeat != this.heat || oldProgress != this.progress) this.setChanged();
        this.stacksChanged = false;
        this.networkPackNT(25);
    }

    private void tryPullHeat() {
        if(this.heat >= MAX_HEAT) return;
        if(this.level.getBlockEntity(this.worldPosition.below()) instanceof IHeatSource source) {
            int difference = source.getHeatStored() - this.heat;
            if(difference == 0) return;
            // The crucible caps the difference before diffusion, unlike the combination oven.
            difference = Math.min(difference, MAX_HEAT - this.heat);
            if(difference > 0) {
                int received = (int) Math.ceil(difference * 0.25D);
                source.useUpHeat(received);
                this.heat += received;
                return;
            }
        }
        this.heat = Math.max(0, this.heat - Math.max(this.heat / 1000, 1));
    }

    private boolean trySmelt() {
        if(this.heat < MAX_HEAT / 2) return false;
        int slot = this.firstSmeltableSlot();
        if(slot == -1) return false;

        int delta = (int) ((this.heat - MAX_HEAT / 2) * 0.05D);
        this.progress += delta;
        this.heat -= delta;

        if(this.progress >= PROCESS_TIME) {
            this.progress = 0;
            Mats.MaterialStack material = CopperCastingRecipes.getMaterial(this.slots.get(slot));
            CrucibleRecipe recipe = this.getLoadedRecipe();
            boolean recipeMaterial = recipe != null
                    && (recipe.getInputAmount(material.material) > 0 || recipe.hasOutput(material.material));
            addToStack(recipeMaterial ? this.recipeStack : this.wasteStack, material);
            this.slots.get(slot).shrink(1);
            this.stacksChanged = true;
        }
        return true;
    }

    private void tryRecipe() {
        CrucibleRecipe recipe = this.getLoadedRecipe();
        if(recipe == null) return;
        if(this.level.getGameTime() % recipe.frequency > 0) return;

        for(Mats.MaterialStack stack : recipe.input) {
            if(getQuantaFromType(this.recipeStack, stack.material) < stack.amount) return;
        }
        for(Mats.MaterialStack stack : this.recipeStack) {
            stack.amount -= recipe.getInputAmount(stack.material);
        }
        for(Mats.MaterialStack out : recipe.output) addToStack(this.recipeStack, out);
        this.stacksChanged = true;
    }

    /** With a recipe loaded only its outputs leave the front spout; without one the whole recipe stack drains. */
    public List<Mats.MaterialStack> getCastableRecipeMaterials() {
        CrucibleRecipe recipe = this.getLoadedRecipe();
        if(recipe == null) return this.recipeStack;
        List<Mats.MaterialStack> toCast = new ArrayList<>();
        for(Mats.MaterialStack stack : this.recipeStack) if(recipe.hasOutput(stack.material)) toCast.add(stack);
        return toCast;
    }

    /**
     * Upstream CrucibleUtil.pourFullStack in safe mode: the first material the mold under the spout accepts,
     * at most 24 quanta per tick. A blocked, absent or full receiver keeps the material in the crucible.
     */
    private void pour(Direction direction, List<Mats.MaterialStack> stacks) {
        if(stacks.isEmpty()) return;
        Vec3 start = new Vec3(this.worldPosition.getX() + 0.5D + direction.getStepX() * 1.875D,
                this.worldPosition.getY() + 0.25D,
                this.worldPosition.getZ() + 0.5D + direction.getStepZ() * 1.875D);
        BlockHitResult hit = this.level.clip(new ClipContext(start, start.add(0, -6, 0),
                ClipContext.Block.COLLIDER, ClipContext.Fluid.ANY, CollisionContext.empty()));
        if(hit.getType() != HitResult.Type.BLOCK || hit.getDirection() != Direction.UP) return;
        if(!(this.level.getBlockEntity(hit.getBlockPos()) instanceof FoundryMoldBlockEntity mold)) return;
        for(Mats.MaterialStack stack : stacks) {
            if(stack.material == null || stack.amount <= 0 || stack.material.smeltable != NTMMaterial.SmeltingBehavior.SMELTABLE) continue;
            int accepted = mold.pour(new Mats.MaterialStack(stack.material, Math.min(stack.amount, CopperCastingRecipes.POUR_QUANTA)));
            if(accepted > 0) {
                stack.amount -= accepted;
                this.stacksChanged = true;
                return;
            }
        }
    }

    public Direction getRecipeDirection() {
        return this.getBlockState().getValue(DummyableBlock.FACING);
    }

    public Direction getWasteDirection() {
        return this.getBlockState().getValue(DummyableBlock.FACING).getOpposite();
    }

    public boolean isItemSmeltable(ItemStack stack) {
        Mats.MaterialStack material = CopperCastingRecipes.getMaterial(stack);
        if(material == null) return false;
        CrucibleRecipe recipe = this.getLoadedRecipe();

        // Every item in the melt table is a single material, so upstream's per-material loop collapses to one pass.
        boolean matchesRecipe = recipe == null;
        int recipeAmount = getQuantaFromType(this.recipeStack, null);
        int wasteAmount = getQuantaFromType(this.wasteStack, null);

        if(recipe != null && recipe.hasOutput(material.material)) {
            // Allows pouring the output material back into the crucible.
            recipeAmount += material.amount;
            matchesRecipe = true;
        } else {
            int recipeInputRequired = recipe != null ? recipe.getInputAmount(material.material) : 0;
            if(recipeInputRequired == 0) {
                wasteAmount += material.amount;
            } else {
                // The maximum is the recipe's ratio scaled up to the recipe stack's capacity.
                int matMaximum = (int) ((long) recipeInputRequired * CAPACITY / recipe.getInputAmount());
                int amountStored = getQuantaFromType(this.recipeStack, material.material);
                matchesRecipe = true;
                recipeAmount += material.amount;
                if(amountStored + material.amount > matMaximum) return false;
            }
        }
        return recipeAmount <= CAPACITY && wasteAmount <= CAPACITY && matchesRecipe;
    }

    private int firstSmeltableSlot() {
        for(int i = 0; i < this.slots.size(); i++) if(this.isItemSmeltable(this.slots.get(i))) return i;
        return -1;
    }

    private void collectItems() {
        AABB intake = new AABB(this.worldPosition.getX() - 0.5D, this.worldPosition.getY() + 0.5D,
                this.worldPosition.getZ() - 0.5D, this.worldPosition.getX() + 1.5D,
                this.worldPosition.getY() + 1D, this.worldPosition.getZ() + 1.5D);
        for(ItemEntity entity : this.level.getEntitiesOfClass(ItemEntity.class, intake)) {
            if(!entity.isAlive() || !this.isItemSmeltable(entity.getItem())) continue;
            for(int i = 0; i < this.slots.size() && !entity.getItem().isEmpty(); i++) {
                if(!this.slots.get(i).isEmpty()) continue;
                this.slots.set(i, entity.getItem().split(1));
                this.setChanged();
            }
            if(entity.getItem().isEmpty()) entity.discard();
        }
    }

    public CrucibleRecipe getLoadedRecipe() {
        return CrucibleRecipes.INSTANCE.recipeNameMap.get(this.recipe);
    }

    private static void addToStack(List<Mats.MaterialStack> stacks, Mats.MaterialStack added) {
        for(Mats.MaterialStack stack : stacks) {
            if(stack.material == added.material) {
                stack.amount += added.amount;
                return;
            }
        }
        stacks.add(added.copy());
    }

    /** Amount of one material, or the total of the list when {@code material} is null. */
    public static int getQuantaFromType(List<Mats.MaterialStack> stacks, NTMMaterial material) {
        int sum = 0;
        for(Mats.MaterialStack stack : stacks) {
            if(stack.material == material) return stack.amount;
            if(material == null) sum += stack.amount;
        }
        return sum;
    }

    /** One scrap item per material in both stacks, as upstream's shovel and block removal do. */
    public List<ItemStack> takeScraps() {
        List<ItemStack> scraps = new ArrayList<>();
        for(Mats.MaterialStack stack : this.recipeStack) addScraps(scraps, stack);
        for(Mats.MaterialStack stack : this.wasteStack) addScraps(scraps, stack);
        if(!this.recipeStack.isEmpty() || !this.wasteStack.isEmpty()) {
            this.recipeStack.clear();
            this.wasteStack.clear();
            this.setChanged();
        }
        return scraps;
    }

    private static void addScraps(List<ItemStack> scraps, Mats.MaterialStack stack) {
        ItemStack scrap = CopperScrapsItem.create(stack);
        if(!scrap.isEmpty()) scraps.add(scrap);
    }

    @Override public boolean canPlaceItem(int slot, ItemStack stack) {
        // Vanilla hopper merges can grow the live stack without consulting the container limit.
        return slot >= 0 && slot < this.slots.size() && this.slots.get(slot).isEmpty() && this.isItemSmeltable(stack);
    }
    @Override public int[] getSlotsForFace(Direction direction) { return new int[] {0, 1, 2, 3, 4, 5, 6, 7, 8}; }
    @Override public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction) { return false; }

    @Override
    public boolean hasPermission(Player player) {
        return this.level != null && !this.level.isClientSide && player.level() == this.level
                && player.containerMenu instanceof MachineCrucibleMenu menu && menu.be == this
                && this.stillValid(player);
    }

    @Override
    public void receiveControl(CompoundTag tag) {
        if(tag == null || !tag.contains("index", Tag.TAG_INT) || !tag.contains("selection", Tag.TAG_STRING)) return;
        if(tag.getInt("index") != 0) return;
        String selection = tag.getString("selection");
        // Upstream stores any string; NEO only accepts "null" or a registered recipe name.
        if(!NO_RECIPE.equals(selection) && !CrucibleRecipes.INSTANCE.recipeNameMap.containsKey(selection)) return;
        if(selection.equals(this.recipe)) return;
        // Changing the recipe keeps both stacks, as upstream does.
        this.recipe = selection;
        this.setChanged();
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putString("recipe", this.recipe);
        tag.putIntArray("rec", writeStack(this.recipeStack));
        tag.putIntArray("was", writeStack(this.wasteStack));
        tag.putInt("progress", this.progress);
        tag.putInt("heat", this.heat);
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.heat = Math.clamp(tag.getInt("heat"), 0, MAX_HEAT);
        this.progress = Math.clamp(tag.getInt("progress"), 0, PROCESS_TIME - 1);
        this.recipe = tag.contains("recipe", Tag.TAG_STRING) ? tag.getString("recipe") : NO_RECIPE;
        readStack(this.recipeStack, tag.getIntArray("rec"));
        readStack(this.wasteStack, tag.getIntArray("was"));
        if(!tag.contains("was") && tag.contains("copper", Tag.TAG_INT)) {
            // Goal 5A crucibles stored a single copper amount; it was unalloyed, so it belongs to the waste stack.
            int copper = Math.clamp(tag.getInt("copper"), 0, CAPACITY);
            if(copper > 0) this.wasteStack.add(new Mats.MaterialStack(Mats.MAT_COPPER, copper));
        }
    }

    private static int[] writeStack(List<Mats.MaterialStack> stacks) {
        int[] data = new int[stacks.size() * 2];
        for(int i = 0; i < stacks.size(); i++) {
            data[i * 2] = stacks.get(i).material.id;
            data[i * 2 + 1] = stacks.get(i).amount;
        }
        return data;
    }

    /** Unknown material IDs and non-positive amounts are dropped instead of becoming null materials. */
    private static void readStack(List<Mats.MaterialStack> stacks, int[] data) {
        stacks.clear();
        for(int i = 0; i + 1 < data.length; i += 2) {
            NTMMaterial material = Mats.matById.get(data[i]);
            int amount = Math.min(data[i + 1], CAPACITY);
            if(material != null && amount > 0) addToStack(stacks, new Mats.MaterialStack(material, amount));
        }
    }

    @Override public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeInt(this.heat);
        buf.writeInt(this.progress);
        buf.writeUtf(this.recipe);
        serializeStack(buf, this.recipeStack);
        serializeStack(buf, this.wasteStack);
    }

    @Override public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.heat = buf.readInt();
        this.progress = buf.readInt();
        this.recipe = buf.readUtf();
        // Both stacks are replaced only after the whole payload was read.
        List<Mats.MaterialStack> syncedRecipe = deserializeStack(buf);
        List<Mats.MaterialStack> syncedWaste = deserializeStack(buf);
        this.recipeStack.clear();
        this.recipeStack.addAll(syncedRecipe);
        this.wasteStack.clear();
        this.wasteStack.addAll(syncedWaste);
    }

    private static void serializeStack(RegistryFriendlyByteBuf buf, List<Mats.MaterialStack> stacks) {
        buf.writeShort(stacks.size());
        for(Mats.MaterialStack stack : stacks) {
            buf.writeInt(stack.material.id);
            buf.writeInt(stack.amount);
        }
    }

    private static List<Mats.MaterialStack> deserializeStack(RegistryFriendlyByteBuf buf) {
        List<Mats.MaterialStack> stacks = new ArrayList<>();
        int size = buf.readShort();
        if(size < 0 || size > MAX_SYNC_ENTRIES) throw new IllegalArgumentException("Invalid crucible stack size " + size);
        for(int i = 0; i < size; i++) {
            // Always read both values so an unknown ID cannot misalign the rest of the packet.
            NTMMaterial material = Mats.matById.get(buf.readInt());
            int amount = buf.readInt();
            if(material != null && amount > 0) stacks.add(new Mats.MaterialStack(material, amount));
        }
        return stacks;
    }

    @Override public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) {
        return new MachineCrucibleMenu(id, inventory, this);
    }
}
