package reviewfixes;

import api.hbm.energymk2.IEnergyProviderMK2;
import api.hbm.energymk2.IEnergyReceiverMK2;
import api.hbm.energymk2.IEnergyReceiverMK2.ConnectionPriority;
import api.hbm.energymk2.PowerNetMK2;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineArcWelderBlockEntity;
import com.hbm.blockentity.machine.MachineSolderingStationBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.machine.MachineSolderingStationBlock;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.recipes.ArcWelderRecipes;
import com.hbm.items.NtmItems;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import java.lang.reflect.Field;
import java.util.Arrays;

/** Real networks, real receiving interfaces and real proxy delegation; the world/registry are isolated fixtures. */
public class PowerRecipeRegression {
    private static int checks;
    static void check(boolean condition, String message) {
        checks++;
        if(!condition) throw new AssertionError(message);
    }

    static class Supply implements IEnergyProviderMK2 {
        long power, used;
        final long speed;
        Supply(long amount, long speed) { power = amount; this.speed = speed; }
        public boolean isLoaded() { return true; }
        public long getPower() { return power; }
        public long getMaxPower() { return 100_000; }
        public void setPower(long value) { used += power - value; power = value; }
        public long getProviderSpeed() { return speed; }
    }

    static class Receiver implements IEnergyReceiverMK2 {
        long power;
        final long capacity, speed, accept;
        final ConnectionPriority priority;
        Receiver(long capacity, long speed, ConnectionPriority priority) { this(capacity, speed, priority, Long.MAX_VALUE); }
        Receiver(long capacity, long speed, ConnectionPriority priority, long accept) {
            this.capacity = capacity; this.speed = speed; this.priority = priority; this.accept = accept;
        }
        public boolean isLoaded() { return true; }
        public long getPower() { return power; }
        public long getMaxPower() { return capacity; }
        public void setPower(long value) { power = value; }
        public long getReceiverSpeed() { return speed; }
        public ConnectionPriority getPriority() { return priority; }
        public long transferPower(long offered) {
            long retained = Math.min(offered, accept);
            return offered - retained + IEnergyReceiverMK2.super.transferPower(retained);
        }
    }

    static void distribution(boolean diode, long available, long[] capacity, long[] speed,
                             ConnectionPriority[] priority, long[] acceptance, long[] expected) {
        PowerNetMK2 net = new PowerNetMK2();
        Receiver[] receivers = new Receiver[capacity.length];
        for(int i = 0; i < receivers.length; i++) {
            receivers[i] = new Receiver(capacity[i], speed[i], priority[i], acceptance[i]);
            net.addReceiver(receivers[i]);
        }
        Supply first = new Supply(available / 3, available / 3);
        Supply second = new Supply(available - available / 3, available - available / 3);
        long leftover;
        if(diode) {
            leftover = net.sendPowerDiode(available);
        } else {
            net.addProvider(first); net.addProvider(second); net.update();
            leftover = first.power + second.power;
        }
        long delivered = 0;
        for(int i = 0; i < receivers.length; i++) {
            check(receivers[i].power == expected[i], (diode ? "diode" : "update") + " allocation " + i
                    + ": got " + receivers[i].power + " expected " + expected[i]);
            delivered += receivers[i].power;
        }
        check(delivered + leftover == available, "source and all recipients conserve energy");
        check(net.energyTracker == delivered, "tracker equals actual delivered energy");
        if(!diode) check(first.used + second.used == delivered, "two provider debits equal delivered energy");
    }

    static void allocation() {
        ConnectionPriority h = ConnectionPriority.HIGH, n = ConnectionPriority.NORMAL, l = ConnectionPriority.LOW;
        for(boolean diode : new boolean[] {false, true}) {
            distribution(diode, 2000, new long[] {10_000,10_000}, new long[] {1000,1000},
                    new ConnectionPriority[] {h,l}, new long[] {99999,99999}, new long[] {1000,1000});
            distribution(diode, 4000, new long[] {10_000,10_000,10_000}, new long[] {1000,2000,1000},
                    new ConnectionPriority[] {h,n,l}, new long[] {99999,99999,99999}, new long[] {1000,2000,1000});
            distribution(diode, 1000, new long[] {2000,1000}, new long[] {2000,1000},
                    new ConnectionPriority[] {n,n}, new long[] {99999,99999}, new long[] {666,333});
            distribution(diode, 500, new long[] {1000,1000}, new long[] {1000,1000},
                    new ConnectionPriority[] {h,l}, new long[] {99999,99999}, new long[] {500,0});
            distribution(diode, 9000, new long[] {1000,2000}, new long[] {1000,2000},
                    new ConnectionPriority[] {h,l}, new long[] {99999,99999}, new long[] {1000,2000});
            distribution(diode, 2000, new long[] {1000,2000}, new long[] {1000,2000},
                    new ConnectionPriority[] {h,l}, new long[] {300,99999}, new long[] {300,1700});
            distribution(diode, 2000, new long[] {0,1000}, new long[] {1000,1000},
                    new ConnectionPriority[] {h,l}, new long[] {99999,99999}, new long[] {0,1000});
            distribution(diode, 2000, new long[] {}, new long[] {}, new ConnectionPriority[] {}, new long[] {}, new long[] {});
            distribution(diode, 0, new long[] {1000}, new long[] {1000}, new ConnectionPriority[] {l},
                    new long[] {99999}, new long[] {0});
        }
    }

    static class Station extends MachineSolderingStationBlock {
        Station() { super(new Block.Properties()); }
        void placeParts(Level level, BlockPos pos, Direction direction) { fillSpace(level, pos, direction, 0); }
    }

    static boolean flag(ProxyComboBlockEntity proxy, String name) throws Exception {
        Field field = ProxyComboBlockEntity.class.getDeclaredField(name);
        field.setAccessible(true);
        return field.getBoolean(proxy);
    }

    static void proxies() throws Exception {
        for(Direction facing : new Direction[] {Direction.NORTH,Direction.SOUTH,Direction.EAST,Direction.WEST}) {
            Level level = new Level();
            Station block = new Station();
            BlockPos pos = new BlockPos(12, 5, 12);
            BlockState state = block.defaultBlockState().setValue(DummyableBlock.TYPE, DummyBlockType.CORE)
                    .setValue(DummyableBlock.FACING, facing);
            level.states.put(pos, state);
            MachineSolderingStationBlockEntity core = (MachineSolderingStationBlockEntity) block.newBlockEntity(pos, state);
            level.put(core);
            block.placeParts(level, pos, facing);
            check(level.states.size() == 4, facing + " default fillSpace has core and three parts");
            int count = 0;
            for(var entry : level.states.entrySet()) {
                if(entry.getKey().equals(pos)) continue;
                check(entry.getValue().getValue(DummyableBlock.TYPE) == DummyBlockType.DUMMY, "placement retains DUMMY schema");
                BlockEntity entity = block.newBlockEntity(entry.getKey(), entry.getValue());
                check(entity instanceof ProxyComboBlockEntity, "DUMMY query creates a proxy");
                ProxyComboBlockEntity proxy = (ProxyComboBlockEntity) entity;
                // The inherited proxy-base fixture resolves an explicitly supplied core, not Minecraft lazy lookup.
                proxy.core = core;
                level.put(proxy);
                check(flag(proxy,"inventory") && flag(proxy,"power") && flag(proxy,"fluid"), "three enabled proxy flags");
                check(Arrays.equals(proxy.getSlotsForFace(Direction.UP), core.getSlotsForFace(Direction.UP)), "inventory slots delegate");
                core.setPower(123);
                check(proxy.getPower() == 123, "power delegates to the core");
                core.slots.set(6, new ItemStack(NtmItems.INGOT_STEEL.get()));
                check(proxy.getItem(6) == core.slots.get(6) && proxy.canTakeItemThroughFace(6, core.slots.get(6), Direction.DOWN),
                        "output contents and extraction delegate");
                check(block.newBlockEntity(entry.getKey(), entry.getValue().setValue(DummyableBlock.TYPE, DummyBlockType.EXTRA))
                        instanceof ProxyComboBlockEntity, "EXTRA still creates proxy");
                count++;
            }
            check(count == 3 && core.getConPos().length == 8, "three proxies and eight unchanged core connection points");
        }
    }

    static void machineIngredientIndex() {
        ArcWelderRecipes recipes = new ArcWelderRecipes();
        recipes.deleteRecipes();
        ArcWelderRecipes.addRecipe(new ItemStack(NtmItems.INGOT_STEEL.get()), 20, 100, null,
                new ComparableStack(NtmItems.INGOT_COPPER.get(), 2));
        MachineArcWelderBlockEntity welder = new MachineArcWelderBlockEntity(new BlockPos(0,0,0), new BlockState());
        check(welder.canPlaceItem(0,new ItemStack(NtmItems.INGOT_COPPER.get())), "machine accepts registered ingredient");
        check(!welder.canPlaceItem(0,ItemStack.EMPTY) && !welder.canPlaceItem(0,new ItemStack(NtmItems.INGOT_STEEL.get())),
                "machine rejects empty and non-ingredient inputs");
        recipes.deleteRecipes();
        check(!welder.canPlaceItem(0,new ItemStack(NtmItems.INGOT_COPPER.get())), "clear removes old machine acceptance");
    }

    public static void main(String[] args) throws Exception {
        allocation(); proxies(); machineIngredientIndex();
        System.out.println("Power and soldering proxies: " + checks + " checks passed");
    }
}
