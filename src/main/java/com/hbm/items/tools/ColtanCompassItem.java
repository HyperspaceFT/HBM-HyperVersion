package com.hbm.items.tools;

import com.hbm.items.LoreItem;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.main.NuclearTechMod;
import com.hbm.main.ServerProxy;
import com.hbm.world.feature.ColtanDepositFeature;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;

/**
 * Original ItemColtanCompass ("Coltass"). The server stores the coltan deposit centre on the stack the first time it
 * ticks in an inventory; the client shows the horizontal distance to it. The needle is the "angle" item property
 * registered in NuclearTechModClient.
 */
public class ColtanCompassItem extends LoreItem {

    public ColtanCompassItem(Properties properties) {
        super(properties);
    }

    public static boolean hasTarget(ItemStack stack) {
        return stack.has(NtmDataComponents.COLTAN_X) && stack.has(NtmDataComponents.COLTAN_Z);
    }

    @Override
    public void inventoryTick(ItemStack stack, Level level, Entity entity, int slotId, boolean isSelected) {

        if(level.isClientSide) {
            if(hasTarget(stack)) {
                double dx = entity.getX() - stack.getOrDefault(NtmDataComponents.COLTAN_X, 0);
                double dz = entity.getZ() - stack.getOrDefault(NtmDataComponents.COLTAN_Z, 0);
                // ServerProxy holds the same info IDs as NuclearTechModClient without loading a client class
                NuclearTechMod.proxy.displayTooltip(Component.literal(((int) Math.sqrt(dx * dx + dz * dz)) + "m"), ServerProxy.ID_COMPASS);
            }
        } else if(!hasTarget(stack) && level instanceof ServerLevel serverLevel) {
            // The same seed-derived centre the deposit feature uses
            ColtanDepositFeature.DepositCentre centre = ColtanDepositFeature.depositCentre(serverLevel.getSeed());
            stack.set(NtmDataComponents.COLTAN_X, centre.x());
            stack.set(NtmDataComponents.COLTAN_Z, centre.z());
        }
    }
}
