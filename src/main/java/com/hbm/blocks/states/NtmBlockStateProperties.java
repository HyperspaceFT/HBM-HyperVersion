package com.hbm.blocks.states;

import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.minecraft.world.level.block.state.properties.IntegerProperty;

public class NtmBlockStateProperties {

    public static final BooleanProperty UP =    BooleanProperty.create("connected_up");
    public static final BooleanProperty DOWN =  BooleanProperty.create("connected_down");
    public static final BooleanProperty NORTH = BooleanProperty.create("connected_north");
    public static final BooleanProperty EAST =  BooleanProperty.create("connected_east");
    public static final BooleanProperty SOUTH = BooleanProperty.create("connected_south");
    public static final BooleanProperty WEST =  BooleanProperty.create("connected_west");

    public static final IntegerProperty META =  IntegerProperty.create("meta", 0, 15);

    /** Paintable cable and duct: the defuser hides the port overlay of a painted block (original metadata 1). */
    public static final BooleanProperty HIDE_OVERLAY = BooleanProperty.create("hide_overlay");
}
