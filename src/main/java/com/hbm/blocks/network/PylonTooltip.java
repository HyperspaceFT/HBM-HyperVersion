package com.hbm.blocks.network;

import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;

import java.util.List;

/** The connection type and range lines of every pylon, connector and substation tooltip (original addInformation, e.g. ConnectorRedWire.java:62-66). */
public class PylonTooltip {

    public static void add(List<Component> components, String type, int range) {
        components.add(Component.translatable("block.hbmsntm.pylon.connection_type").withStyle(ChatFormatting.GOLD)
                .append(Component.translatable("block.hbmsntm.pylon.type_" + type).withStyle(ChatFormatting.YELLOW)));
        components.add(Component.translatable("block.hbmsntm.pylon.connection_range").withStyle(ChatFormatting.GOLD)
                .append(Component.translatable("block.hbmsntm.pylon.range", range).withStyle(ChatFormatting.YELLOW)));
    }
}
