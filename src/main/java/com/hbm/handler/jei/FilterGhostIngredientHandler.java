package com.hbm.handler.jei;

import com.hbm.inventory.SlotPattern;
import com.hbm.network.toserver.CompoundTagControl;
import mezz.jei.api.gui.handlers.IGhostIngredientHandler;
import mezz.jei.api.ingredients.ITypedIngredient;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.client.renderer.Rect2i;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.neoforged.neoforge.network.PacketDistributor;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;

/**
 * JEI drag and drop into phantom filter slots, the counterpart of the original's NEI handler (GuiInfoContainer.java:353-376): the
 * client sends the "slot" control with the slot and the stack; the block entity checks both (IControlReceiverFilter).
 */
public class FilterGhostIngredientHandler<T extends AbstractContainerScreen<?>> implements IGhostIngredientHandler<T> {

    private final Function<T, BlockEntity> blockEntity;

    public FilterGhostIngredientHandler(Function<T, BlockEntity> blockEntity) {
        this.blockEntity = blockEntity;
    }

    @Override
    public <I> List<Target<I>> getTargetsTyped(T gui, ITypedIngredient<I> ingredient, boolean doStart) {
        List<Target<I>> targets = new ArrayList<>();
        if(ingredient.getItemStack().isEmpty()) return targets;

        BlockEntity be = this.blockEntity.apply(gui);
        if(be == null) return targets;

        for(Slot slot : gui.getMenu().slots) {
            if(!(slot instanceof SlotPattern)) continue;

            Rect2i area = new Rect2i(gui.getGuiLeft() + slot.x, gui.getGuiTop() + slot.y, 16, 16);
            int index = slot.getContainerSlot();

            targets.add(new Target<>() {
                @Override public Rect2i getArea() { return area; }

                @Override
                public void accept(I value) {
                    ItemStack stack = ingredient.getItemStack().orElse(ItemStack.EMPTY);
                    if(stack.isEmpty() || Minecraft.getInstance().level == null) return;

                    CompoundTag data = new CompoundTag();
                    data.putInt("slot", index);
                    data.put("stack", stack.copyWithCount(1).save(Minecraft.getInstance().level.registryAccess()));
                    PacketDistributor.sendToServer(new CompoundTagControl(data, be.getBlockPos()));
                }
            });
        }

        return targets;
    }

    @Override
    public void onComplete() { }
}
