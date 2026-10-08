package com.hbm.items.component;

import com.hbm.main.NuclearTechMod;
import com.mojang.serialization.Codec;
import net.minecraft.core.component.DataComponentType;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.util.ExtraCodecs;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;

public class NtmDataComponents {

    private static final DeferredRegister<DataComponentType<?>> DATA_COMPONENT_TYPES = DeferredRegister.create(Registries.DATA_COMPONENT_TYPE, NuclearTechMod.MODID);

    public static final DeferredHolder<DataComponentType<?>, DataComponentType<Integer>> META = DATA_COMPONENT_TYPES.register("meta", () -> DataComponentType.<Integer>builder().persistent(ExtraCodecs.NON_NEGATIVE_INT).networkSynchronized(ByteBufCodecs.INT).build());
    // Coltan compass target, the original colX / colZ tag; block coordinates, may be negative
    public static final DeferredHolder<DataComponentType<?>, DataComponentType<Integer>> COLTAN_X = DATA_COMPONENT_TYPES.register("coltan_x", () -> DataComponentType.<Integer>builder().persistent(Codec.INT).networkSynchronized(ByteBufCodecs.INT).build());
    public static final DeferredHolder<DataComponentType<?>, DataComponentType<Integer>> COLTAN_Z = DATA_COMPONENT_TYPES.register("coltan_z", () -> DataComponentType.<Integer>builder().persistent(Codec.INT).networkSynchronized(ByteBufCodecs.INT).build());

    public static void register(IEventBus eventBus) { DATA_COMPONENT_TYPES.register(eventBus); }
}
