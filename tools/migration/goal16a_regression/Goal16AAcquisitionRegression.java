package com.hbm.blockentity.machine;

import com.hbm.handler.jei.CrucibleCastingRecipeHandler;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.Mats.MaterialStack;
import com.hbm.inventory.material.NTMMaterial;
import com.hbm.inventory.recipes.CopperCastingRecipes;
import com.hbm.inventory.recipes.CrucibleRecipe;
import com.hbm.inventory.recipes.CrucibleRecipes;
import com.hbm.inventory.recipes.anvil.AnvilSmithingIngotMoldRecipe;
import com.hbm.items.NtmItems;
import mezz.jei.api.gui.builder.IDrawableBuilder;
import mezz.jei.api.gui.builder.IRecipeLayoutBuilder;
import mezz.jei.api.gui.builder.IRecipeSlotBuilder;
import mezz.jei.api.gui.builder.IRecipeSlotRichTooltipCallback;
import mezz.jei.api.gui.drawable.IDrawable;
import mezz.jei.api.helpers.IGuiHelper;
import mezz.jei.api.recipe.RecipeIngredientRole;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;

import java.util.ArrayList;
import java.util.List;

public final class Goal16AAcquisitionRegression {
    private static int checks;

    private static void check(boolean condition, String message) {
        checks++;
        if(!condition) throw new AssertionError(message);
    }

    private static Level level() {
        Level level = new Level();
        level.manualClock = true;
        return level;
    }

    private static FoundryMoldBlockEntity mold(Level level, BlockPos pos, Item item) {
        FoundryMoldBlockEntity mold = new FoundryMoldBlockEntity(pos, new BlockState());
        level.put(mold);
        if(item != null) check(mold.insertMold(new ItemStack(item)), "one reusable mold inserted");
        return mold;
    }

    private static String column(double x, double z) {
        return (int)Math.floor(x) + "," + (int)Math.floor(z);
    }

    private static void aimNorth(Level level, BlockPos crucible, BlockPos target) {
        double x = crucible.getX() + 0.5D;
        double z = crucible.getZ() + 0.5D - 1.875D;
        level.columnHits.put(column(x, z), new BlockHitResult(HitResult.Type.BLOCK, target, Direction.UP));
    }

    private static void tickCrucible(MachineCrucibleBlockEntity crucible, Level level) {
        crucible.updateEntity();
        level.time++;
    }

    private static void finiteCrucibleToIngot() {
        CrucibleRecipes.INSTANCE.registerDefaults();
        CrucibleRecipe hss = CrucibleRecipes.INSTANCE.recipeNameMap.get("crucible.hss");
        check(hss != null && hss.frequency == 9, "use the registered HSS crucible recipe");
        check(hss.getInputAmount(Mats.MAT_STEEL) == 40
                        && hss.getInputAmount(Mats.MAT_TUNGSTEN) == 24
                        && hss.getInputAmount(Mats.MAT_COBALT) == 8
                        && hss.hasOutput(Mats.MAT_DURA),
                "finite source ledger uses 40 steel, 24 tungsten, 8 cobalt -> 72 Dura quanta");

        Level level = level();
        BlockPos cruciblePos = new BlockPos(0, 1, 0);
        BlockPos moldPos = new BlockPos(0, 0, -2);
        MachineCrucibleBlockEntity crucible = new MachineCrucibleBlockEntity(cruciblePos, new BlockState());
        level.put(crucible);
        FoundryMoldBlockEntity mold = mold(level, moldPos, NtmItems.MOLD_INGOT.get());
        BlockState state = new BlockState();
        state.facing = Direction.NORTH;
        level.states.put(cruciblePos, state);
        aimNorth(level, cruciblePos, moldPos);
        crucible.recipe = "crucible.hss";
        crucible.heat = MachineCrucibleBlockEntity.MAX_HEAT;
        crucible.recipeStack.add(new MaterialStack(Mats.MAT_STEEL, 40));
        crucible.recipeStack.add(new MaterialStack(Mats.MAT_TUNGSTEN, 24));
        crucible.recipeStack.add(new MaterialStack(Mats.MAT_COBALT, 8));

        tickCrucible(crucible, level);
        check(MachineCrucibleBlockEntity.getQuantaFromType(crucible.recipeStack, Mats.MAT_DURA) == 48
                        && mold.amount == 24 && mold.type == Mats.MAT_DURA,
                "actual crucible recipe alloys finite quanta and actual front pour transfers 24");
        tickCrucible(crucible, level);
        tickCrucible(crucible, level);
        check(MachineCrucibleBlockEntity.getQuantaFromType(crucible.recipeStack, Mats.MAT_DURA) == 0
                        && mold.amount == CopperCastingRecipes.INGOT_QUANTA
                        && mold.type == Mats.MAT_DURA,
                "two more actual 24-quanta pours fill exactly one ingot mold");
        check(MachineCrucibleBlockEntity.getQuantaFromType(crucible.recipeStack, Mats.MAT_STEEL) == 0
                        && MachineCrucibleBlockEntity.getQuantaFromType(crucible.recipeStack, Mats.MAT_TUNGSTEN) == 0,
                "HSS input recipe consumes its exact ingredient quanta");

        for(int tick = 0; tick < 200; tick++) mold.updateEntity();
        check(mold.amount == 0 && mold.type == null && mold.cooloff == 200,
                "200 full idle updates complete the cast and reset mold state");
        ItemStack output = mold.slots.get(1);
        check(output.is(NtmItems.INGOT_DURA_STEEL.get()) && output.getCount() == 1,
                "the filled ingot mold creates one actual Dura steel item");
        check(mold.pour(new MaterialStack(Mats.MAT_DURA, 24)) == 0
                        && mold.slots.get(1).is(NtmItems.INGOT_DURA_STEEL.get()),
                "occupied output slot blocks further molten input without losing the output");
    }

    private static void oldPlatePathsAndTypeCapacity() {
        Object[][] plateInputs = {
                {Mats.MAT_COPPER, 5}, {Mats.MAT_TUNGSTEN, 6}, {Mats.MAT_STEEL, 11}, {Mats.MAT_DURA, 12}
        };
        for(Object[] input : plateInputs) {
            NTMMaterial material = (NTMMaterial)input[0];
            int meta = (int)input[1];
            Level level = level();
            FoundryMoldBlockEntity mold = mold(level, new BlockPos(meta, 0, 0), NtmItems.MOLD_PLATE_CAST.get());
            check(mold.getCapacity() == CopperCastingRecipes.PLATE_QUANTA
                            && mold.pour(new MaterialStack(material, CopperCastingRecipes.PLATE_QUANTA)) == CopperCastingRecipes.PLATE_QUANTA,
                    material.names[0] + " plate buffer still uses 216 quanta");
            for(int tick = 0; tick < 200; tick++) mold.updateEntity();
            ItemStack output = mold.slots.get(1);
            check(output.is(NtmItems.CAST_PLATE.get()) && output.component().equals(Integer.toString(meta))
                            && output.getCount() == 1,
                    material.names[0] + " plate output and metadata remain unchanged");
        }

        Level level = level();
        FoundryMoldBlockEntity ingot = mold(level, new BlockPos(20, 0, 0), NtmItems.MOLD_INGOT.get());
        check(ingot.getCapacity() == CopperCastingRecipes.INGOT_QUANTA, "ingot mold capacity is fixed at 72");
        check(ingot.pour(new MaterialStack(Mats.MAT_COPPER, 72)) == 0
                        && ingot.pour(new MaterialStack(Mats.MAT_STEEL, 72)) == 0
                        && ingot.pour(new MaterialStack(Mats.MAT_TUNGSTEN, 72)) == 0,
                "ingot mold rejects copper, steel and tungsten");
        check(ingot.pour(new MaterialStack(Mats.MAT_DURA, 100)) == 72 && ingot.amount == 72,
                "oversized Dura pour is bounded at the ingot capacity");
        check(ingot.pour(new MaterialStack(Mats.MAT_DURA, 1)) == 0,
                "full ingot mold accepts no extra Dura quanta");
    }

    private static void saveAndNetworkBounds() {
        Level level = level();
        FoundryMoldBlockEntity ingot = mold(level, new BlockPos(30, 0, 0), NtmItems.MOLD_INGOT.get());
        check(ingot.pour(new MaterialStack(Mats.MAT_DURA, 48)) == 48, "seed partial Dura ingot buffer");

        net.minecraft.nbt.CompoundTag tag = new net.minecraft.nbt.CompoundTag();
        invoke(ingot, "saveAdditional", tag);
        FoundryMoldBlockEntity loaded = new FoundryMoldBlockEntity(new BlockPos(31, 0, 0), new BlockState());
        level.put(loaded);
        invoke(loaded, "loadAdditional", tag);
        check(loaded.slots.get(0).is(NtmItems.MOLD_INGOT.get()) && loaded.amount == 48 && loaded.type == Mats.MAT_DURA,
                "ingot NBT roundtrip retains mold identity and Dura quanta");

        net.minecraft.nbt.CompoundTag over = tag.copy();
        over.putInt("amount", 500);
        FoundryMoldBlockEntity clamped = new FoundryMoldBlockEntity(new BlockPos(32, 0, 0), new BlockState());
        level.put(clamped);
        invoke(clamped, "loadAdditional", over);
        check(clamped.type == Mats.MAT_DURA && clamped.amount == 72,
                "oversized saved ingot buffer clamps to its fixed 72-quanta capacity");

        net.minecraft.nbt.CompoundTag mismatch = tag.copy();
        mismatch.putInt("type", Mats.MAT_STEEL.id);
        FoundryMoldBlockEntity invalid = new FoundryMoldBlockEntity(new BlockPos(33, 0, 0), new BlockState());
        level.put(invalid);
        invoke(invalid, "loadAdditional", mismatch);
        check(invalid.type == null && invalid.amount == 0,
                "incompatible material state in an ingot mold is safely discarded");

        Level plateLevel = level();
        FoundryMoldBlockEntity plate = mold(plateLevel, new BlockPos(34, 0, 0), NtmItems.MOLD_PLATE_CAST.get());
        check(plate.pour(new MaterialStack(Mats.MAT_COPPER, 100)) == 100, "seed legacy copper plate state");
        net.minecraft.nbt.CompoundTag old = new net.minecraft.nbt.CompoundTag();
        invoke(plate, "saveAdditional", old);
        FoundryMoldBlockEntity oldLoaded = new FoundryMoldBlockEntity(new BlockPos(35, 0, 0), new BlockState());
        plateLevel.put(oldLoaded);
        invoke(oldLoaded, "loadAdditional", old);
        check(oldLoaded.slots.get(0).is(NtmItems.MOLD_PLATE_CAST.get())
                        && oldLoaded.amount == 100 && oldLoaded.type == Mats.MAT_COPPER,
                "valid legacy plate NBT retains material, amount and plate mold");

        RegistryFriendlyByteBuf packet = new RegistryFriendlyByteBuf();
        ingot.serialize(packet);
        FoundryMoldBlockEntity client = new FoundryMoldBlockEntity(new BlockPos(36, 0, 0), new BlockState());
        client.deserialize(packet);
        check(client.slots.get(0).is(NtmItems.MOLD_INGOT.get()) && client.amount == 48 && client.type == Mats.MAT_DURA,
                "network roundtrip retains bounded ingot mold state");
    }

    private static void invoke(FoundryMoldBlockEntity be, String method, net.minecraft.nbt.CompoundTag tag) {
        try {
            var target = be.getClass().getDeclaredMethod(method, net.minecraft.nbt.CompoundTag.class,
                    net.minecraft.core.HolderLookup.Provider.class);
            target.setAccessible(true);
            target.invoke(be, tag, null);
        } catch(ReflectiveOperationException e) {
            throw new AssertionError(method + " failed", e);
        }
    }

    private static final class Slot implements IRecipeSlotBuilder {
        final RecipeIngredientRole role;
        final List<ItemStack> stacks = new ArrayList<>();
        Slot(RecipeIngredientRole role) { this.role = role; }
        @Override public IRecipeSlotBuilder addItemStack(ItemStack stack) { stacks.add(stack); return this; }
        @Override public IRecipeSlotBuilder addRichTooltipCallback(IRecipeSlotRichTooltipCallback callback) { return this; }
    }

    private static final class Layout implements IRecipeLayoutBuilder {
        final List<Slot> slots = new ArrayList<>();
        @Override public IRecipeSlotBuilder addSlot(RecipeIngredientRole role, int x, int y) {
            Slot slot = new Slot(role);
            slots.add(slot);
            return slot;
        }
    }

    private static final class Gui implements IGuiHelper {
        @Override public IDrawableBuilder drawableBuilder(ResourceLocation texture, int u, int v, int w, int h) {
            return new IDrawableBuilder() {
                @Override public IDrawableBuilder setTextureSize(int width, int height) { return this; }
                @Override public IDrawable build() { return new IDrawable() {}; }
            };
        }
        @Override public IDrawable createDrawableItemLike(net.minecraft.world.level.ItemLike item) { return new IDrawable() {}; }
    }

    private static boolean liquid(ItemStack stack, NTMMaterial material, int amount) {
        MaterialStack actual = com.hbm.items.CopperScrapsItem.getMats(stack);
        return actual != null && actual.material == material && actual.amount == amount
                && com.hbm.items.CopperScrapsItem.isLiquid(stack);
    }

    private static void castingJei() {
        CrucibleCastingRecipeHandler handler = new CrucibleCastingRecipeHandler(new Gui());
        List<CrucibleCastingRecipeHandler.Casting> recipes = CrucibleCastingRecipeHandler.getRecipes();
        check(recipes.size() == 5 && recipes.getLast().material() == Mats.MAT_DURA && recipes.getLast().ingot(),
                "JEI lists four existing plate recipes plus one Dura ingot casting");
        Layout layout = new Layout();
        handler.setRecipe(layout, recipes.getLast(), null);
        check(layout.slots.size() == 4
                        && layout.slots.get(0).role == RecipeIngredientRole.INPUT
                        && liquid(layout.slots.get(0).stacks.get(0), Mats.MAT_DURA, CopperCastingRecipes.INGOT_QUANTA),
                "JEI ingot row displays a finite 72-quanta liquid Dura input");
        check(layout.slots.get(1).stacks.get(0).is(NtmItems.MOLD_INGOT.get())
                        && layout.slots.get(2).stacks.get(0).is(com.hbm.blocks.NtmBlocks.FOUNDRY_MOLD.asItem())
                        && layout.slots.get(3).stacks.get(0).is(NtmItems.INGOT_DURA_STEEL.get()),
                "JEI ingot row displays the correct mold, foundry and actual ingot output");
    }

    private static void smithingRecipe() {
        AnvilSmithingIngotMoldRecipe recipe = new AnvilSmithingIngotMoldRecipe();
        ItemStack pattern = new ItemStack(Items.IRON_INGOT);
        ItemStack blanks = new ItemStack(NtmItems.MOLD_BASE.get(), 2);
        check(recipe.getTier() == 1 && !recipe.isShapeless(), "ingot mold recipe is ordered tier-1 smithing");
        check(recipe.matchesInt(pattern, blanks) == 0
                        && recipe.getSimpleOutput().is(NtmItems.MOLD_INGOT.get()),
                "one c:ingots reference and a blank mold yield the new ingot mold");
        check(recipe.amountConsumed(0, false) == 0 && recipe.amountConsumed(1, false) == 1,
                "pattern is reusable and only one blank mold is consumed");
        for(int i = 0; i < 2; i++) {
            check(recipe.matchesInt(pattern, blanks) == 0, "the same reference matches another blank");
            ItemStack output = recipe.getOutput(pattern, blanks);
            pattern.shrink(recipe.amountConsumed(0, false));
            blanks.shrink(recipe.amountConsumed(1, false));
            check(output.is(NtmItems.MOLD_INGOT.get()), "one new ingot mold output produced");
        }
        check(pattern.getCount() == 1 && blanks.isEmpty(), "two blank molds are used with one persistent reference");
        check(recipe.matchesInt(new ItemStack(Items.IRON_INGOT, 2), new ItemStack(NtmItems.MOLD_BASE.get())) == -1,
                "pattern stacks greater than one reject");
        check(recipe.matchesInt(new ItemStack(NtmItems.MOLD_BASE.get()), new ItemStack(Items.IRON_INGOT)) == -1,
                "mirrored reference and mold reject");
        check(recipe.matchesInt(new ItemStack(new Item("minecraft:stick")), new ItemStack(NtmItems.MOLD_BASE.get())) == -1,
                "non-ingot item rejects");
    }

    public static void main(String[] args) {
        finiteCrucibleToIngot();
        oldPlatePathsAndTypeCapacity();
        saveAndNetworkBounds();
        castingJei();
        smithingRecipe();
        System.out.println("Goal 16A acquisition: " + checks + " assertions passed");
    }
}
