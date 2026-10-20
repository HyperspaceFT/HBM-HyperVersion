package com.hbm.blockentity.machine.rbmk;

/**
 * Original TileEntityRBMKConsole.ColumnType (:502-523), the column kind shown on the RBMK console. Top-level here because the
 * console itself arrives later (Goal24E).
 */
public enum RBMKColumnType {
    BLANK(0),
    FUEL(10),
    FUEL_SIM(90),
    CONTROL(20),
    CONTROL_AUTO(30),
    BOILER(40),
    MODERATOR(50),
    ABSORBER(60),
    REFLECTOR(70),
    OUTGASSER(80),
    BREEDER(100),
    STORAGE(110),
    COOLER(120),
    HEATEX(130);

    public final int offset;

    RBMKColumnType(int offset) {
        this.offset = offset;
    }
}
