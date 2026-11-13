package com.hbm.items.tools;

import com.hbm.blocks.ILookOverlay;
import com.hbm.blocks.ITooltipProvider;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.network.ConveyorBaseBlock;
import com.hbm.blocks.network.CraneBaseBlock;
import com.hbm.blocks.network.ConveyorBlock;
import com.hbm.inventory.MetaHelper;
import com.hbm.items.EnumMultiItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.TagsUtil;
import com.hbm.util.i18n.I18nUtil;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.client.event.RenderGuiEvent;
import net.neoforged.neoforge.common.CommonHooks;
import net.neoforged.neoforge.event.level.BlockEvent;
import net.neoforged.neoforge.client.model.generators.ItemModelBuilder;
import net.neoforged.neoforge.client.model.generators.ItemModelProvider;
import net.neoforged.neoforge.client.model.generators.ModelFile;

import javax.annotation.Nullable;
import java.util.ArrayList;
import java.util.List;

/**
 * Original ItemConveyorWand: places conveyor belts. A crouching click places a single belt; otherwise the first click
 * stores a start point on the stack and the second builds a route between the two points, consuming one wand per belt.
 * The start point lives in the stack's custom data (x, y, z, side, count), like the fluid identifier's types.
 */
public class ConveyorWandItem extends EnumMultiItem implements ILookOverlay {

    public enum ConveyorType {
        REGULAR,
        EXPRESS,
        DOUBLE,
        TRIPLE
    }

    public ConveyorWandItem(Properties properties) {
        super(properties, ConveyorType.class, true, true);
    }

    public static ConveyorType getType(ItemStack stack) {
        int meta = MetaHelper.getMeta(stack);
        return meta >= 0 && meta < ConveyorType.values().length ? ConveyorType.values()[meta] : ConveyorType.REGULAR;
    }

    public static Block getConveyorBlock(ConveyorType type) {
        return switch(type) {
            case EXPRESS -> NtmBlocks.CONVEYOR_EXPRESS.get();
            case DOUBLE -> NtmBlocks.CONVEYOR_DOUBLE.get();
            case TRIPLE -> NtmBlocks.CONVEYOR_TRIPLE.get();
            default -> NtmBlocks.CONVEYOR.get();
        };
    }

    /** Only the regular wand places lifts and chutes (ItemConveyorWand.java:70-72). */
    public static boolean hasSnakesAndLadders(ConveyorType type) {
        return type == ConveyorType.REGULAR;
    }

    /** The item model of each type is the matching straight belt (original ClientProxy.java:615 drew the block). */
    @Override
    public void registerItemModel(ItemModelProvider provider, ResourceLocation modelLocation) {
        ItemModelBuilder builder = provider.getBuilder(modelLocation.toString());
        for(ConveyorType type : ConveyorType.values()) {
            ResourceLocation block = BuiltInRegistries.BLOCK.getKey(getConveyorBlock(type));
            builder.override()
                    .predicate(NuclearTechMod.withDefaultNamespace("item_meta"), type.ordinal())
                    .model(new ModelFile.UncheckedModelFile(ResourceLocation.fromNamespaceAndPath(block.getNamespace(), "block/" + block.getPath() + "_straight")))
                    .end();
        }
        builder.parent(new ModelFile.UncheckedModelFile(NuclearTechMod.withDefaultNamespace("block/conveyor_straight")));
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> tooltip, TooltipFlag flag) {
        if(Screen.hasShiftDown()) {
            for(String s : I18nUtil.resolveKeyArray(this.getDescriptionId() + ".desc")) {
                tooltip.add(Component.literal(s).withStyle(ChatFormatting.YELLOW));
            }
            if(hasSnakesAndLadders(getType(stack))) {
                tooltip.add(Component.translatable(this.getDescriptionId() + ".vertical.desc").withStyle(ChatFormatting.AQUA));
            }
        } else {
            tooltip.add(ITooltipProvider.holdShiftHint());
        }
    }

    public static boolean hasStart(ItemStack stack) {
        return TagsUtil.hasCustomData(stack);
    }

    public static void clearStart(ItemStack stack) {
        stack.remove(DataComponents.CUSTOM_DATA);
    }

    @Override
    public InteractionResult useOn(UseOnContext context) {

        // the original had one hand; the wand counts and keeps its start point by the main hand
        Player player = context.getPlayer();
        if(player == null || context.getHand() != InteractionHand.MAIN_HAND) return InteractionResult.PASS;

        Level level = context.getLevel();
        ItemStack stack = context.getItemInHand();
        BlockPos pos = context.getClickedPos();
        Direction side = context.getClickedFace();
        ConveyorType type = getType(stack);
        boolean hasStart = hasStart(stack);

        if(player.isShiftKeyDown() && !hasStart) {
            if(!level.isClientSide) this.placeSingle(level, player, stack, pos, side, type);
            return InteractionResult.sidedSuccess(level.isClientSide);
        }

        side = snapSide(level, pos, side, hasStart);

        if(!level.isClientSide) {
            if(!hasStart) {
                CompoundTag tag = new CompoundTag();
                tag.putInt("x", pos.getX());
                tag.putInt("y", pos.getY());
                tag.putInt("z", pos.getZ());
                tag.putInt("side", side.get3DDataValue());
                // only drives the client preview's colour; the second click counts again (ItemConveyorWand.java:167-178)
                tag.putInt("count", player.getAbilities().instabuild ? 256 : countWands(player, type));
                TagsUtil.putCustomData(stack, tag);
            } else {
                CompoundTag tag = TagsUtil.getCustomData(stack);
                BlockPos start = new BlockPos(tag.getInt("x"), tag.getInt("y"), tag.getInt("z"));
                Direction startSide = Direction.from3DDataValue(tag.getInt("side"));
                clearStart(stack);
                this.build(level, player, type, start, startSide, pos, side);
            }
        } else if(hasStart) {
            NuclearTechMod.proxy.clearConveyorWandPreview();
        }

        return InteractionResult.sidedSuccess(level.isClientSide);
    }

    /**
     * ItemConveyorWand.java:142-156: clicking a bendable belt snaps to its free end, the output for the first click and the
     * input for the second, so lines connect without aiming at the thin belt edge.
     */
    public static Direction snapSide(Level level, BlockPos pos, Direction side, boolean hasStart) {
        if(level.getBlockState(pos).getBlock() instanceof ConveyorBlock bendable) {
            Direction moveDir = hasStart ? bendable.getInputDirection(level, pos) : bendable.getOutputDirection(level, pos);
            if(level.getBlockState(pos.relative(moveDir)).canBeReplaced()) return moveDir;
        }
        return side;
    }

    /**
     * ItemConveyorWand.java:106-140. A regular wand turns the clicked straight regular belt into a lift (top face) or a chute
     * (bottom face) before it checks the target, so the belt changes even when the target is blocked.
     */
    private void placeSingle(Level level, Player player, ItemStack stack, BlockPos pos, Direction side, ConveyorType type) {

        BlockState onState = level.getBlockState(pos);
        Block onBlock = onState.getBlock();

        if(hasSnakesAndLadders(type) && onBlock == NtmBlocks.CONVEYOR.get() && onState.getValue(ConveyorBlock.SHAPE) == ConveyorBlock.Shape.STRAIGHT) {
            Direction facing = onState.getValue(ConveyorBaseBlock.HORIZONTAL_FACING);
            if(side == Direction.UP) {
                onBlock = NtmBlocks.CONVEYOR_LIFT.get();
                level.setBlock(pos, ((ConveyorBaseBlock) onBlock).stateFor(level, pos, facing), 3);
            } else if(side == Direction.DOWN) {
                onBlock = NtmBlocks.CONVEYOR_CHUTE.get();
                level.setBlock(pos, ((ConveyorBaseBlock) onBlock).stateFor(level, pos, facing), 3);
            }
        }

        Block toPlace = getConveyorBlock(type);
        if(hasSnakesAndLadders(type)) {
            if(onBlock == NtmBlocks.CONVEYOR_LIFT.get() && side == Direction.UP) toPlace = NtmBlocks.CONVEYOR_LIFT.get();
            if(onBlock == NtmBlocks.CONVEYOR_CHUTE.get() && side == Direction.DOWN) toPlace = NtmBlocks.CONVEYOR_CHUTE.get();
        }

        BlockPos target = pos.relative(side);

        if(level.getBlockState(target).canBeReplaced()) {
            level.setBlock(target, ((ConveyorBaseBlock) toPlace).stateFor(level, target, player.getDirection().getOpposite()), 3);
            stack.consume(1, player);
        }
    }

    /**
     * ItemConveyorWand.java:180-223, server only. The original capped the route with the count stored at the first click and
     * then took whatever wands were left, so a route still got built after the wands were dropped; here the second click
     * counts the main inventory again and builds only when there are enough.
     */
    private void build(Level level, Player player, ConveyorType type, BlockPos start, Direction startSide, BlockPos end, Direction endSide) {

        boolean creative = player.getAbilities().instabuild;
        int max = creative ? 256 : countWands(player, type);
        Route route = construct(level, type, player, start, startSide, end, endSide, max);

        if(route.result() > 0) {
            for(Placement placement : route.placements()) {
                level.setBlock(placement.pos(), placement.stateAt(level, placement.pos()), 3);
            }

            if(!creative) {
                int toRemove = route.result();
                for(ItemStack inventoryStack : player.getInventory().items) {
                    if(inventoryStack.getItem() == this && getType(inventoryStack) == type) {
                        int removing = Math.min(toRemove, inventoryStack.getCount());
                        inventoryStack.shrink(removing);
                        toRemove -= removing;
                    }
                    if(toRemove <= 0) break;
                }
            }

            player.sendSystemMessage(Component.translatable(this.getDescriptionId() + ".built"));
        } else if(route.result() == 0) {
            player.sendSystemMessage(Component.translatable(this.getDescriptionId() + ".not_enough"));
        } else {
            player.sendSystemMessage(Component.translatable(this.getDescriptionId() + ".obstructed"));
        }
    }

    /** Wands of this type in the 36 main inventory slots, start point or not. */
    public static int countWands(Player player, ConveyorType type) {
        int count = 0;
        for(ItemStack inventoryStack : player.getInventory().items) {
            if(inventoryStack.getItem() instanceof ConveyorWandItem && getType(inventoryStack) == type) {
                count += inventoryStack.getCount();
            }
        }
        return count;
    }

    /**
     * ItemConveyorWand.java:233-246: the start point is dropped once the stack is not held and the main hand holds no wand of
     * the same type. The server owns the stack, so only it clears; the client keeps the build preview up to date.
     */
    @Override
    public void inventoryTick(ItemStack stack, Level level, Entity entity, int slot, boolean selected) {
        if(!(entity instanceof Player player)) return;

        if(!selected && hasStart(stack)) {
            ItemStack held = player.getMainHandItem();
            if(held.isEmpty() || held.getItem() != this || getType(held) != getType(stack)) {
                if(!level.isClientSide) clearStart(stack);
                else NuclearTechMod.proxy.clearConveyorWandPreview();
            }
        }

        if(level.isClientSide && selected) {
            NuclearTechMod.proxy.updateConveyorWandPreview(stack, player);
        }
    }

    private static boolean breakingLine = false;

    /**
     * ItemConveyorWand.java:311-359: a crouching creative player holding a wand who breaks a belt also breaks the belts
     * connected to its input and output, each with its own break event and no drops. Each walk stops after 31 belts; the
     * belt being broken is still standing, so the upstream walk passes it and runs on downstream, which leaves 29 for the
     * downstream walk, as in the original.
     * Items have no start-break hook in 1.21, so this runs from the block break event; the extra breaks post that event
     * again, which the flag ignores.
     */
    public static void onBlockBreak(BlockEvent.BreakEvent event) {
        if(breakingLine || event.isCanceled()) return;
        if(!(event.getPlayer() instanceof ServerPlayer player)) return;
        if(!player.isShiftKeyDown() || !player.getAbilities().instabuild) return;
        if(!(player.getMainHandItem().getItem() instanceof ConveyorWandItem)) return;
        if(!(event.getLevel() instanceof Level level) || level.isClientSide) return;
        if(!(event.getState().getBlock() instanceof ConveyorBaseBlock conveyor)) return;

        BlockPos pos = event.getPos();
        Direction input = conveyor.getInputDirection(level, pos);
        Direction output = conveyor.getOutputDirection(level, pos);

        breakingLine = true;
        try {
            breakExtra(level, player, pos.relative(input), 32);
            breakExtra(level, player, pos.relative(output), 32);
        } finally {
            breakingLine = false;
        }
    }

    private static void breakExtra(Level level, ServerPlayer player, BlockPos pos, int depth) {
        depth--;
        if(depth <= 0) return;

        BlockState state = level.getBlockState(pos);
        if(!(state.getBlock() instanceof ConveyorBaseBlock conveyor)) return;

        Direction input = conveyor.getInputDirection(level, pos);
        Direction output = conveyor.getOutputDirection(level, pos);

        if(CommonHooks.fireBlockBreak(level, player.gameMode.getGameModeForPlayer(), player, pos, state).isCanceled()) return;

        BlockState destroyed = state.getBlock().playerWillDestroy(level, pos, state, player);
        if(destroyed.onDestroyedByPlayer(level, pos, player, false, level.getFluidState(pos))) {
            destroyed.getBlock().destroy(level, pos, destroyed);
        }

        breakExtra(level, player, pos.relative(input), depth);
        breakExtra(level, player, pos.relative(output), depth);
    }

    /** ItemConveyorWand.java:505-517 */
    @Override
    @OnlyIn(Dist.CLIENT)
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        Player player = NuclearTechMod.proxy.me();
        if(player == null || !player.isShiftKeyDown() || !player.getAbilities().instabuild || player.getMainHandItem().getItem() != this) return;

        Block block = level.getBlockState(pos).getBlock();
        if(block instanceof ConveyorBaseBlock) {
            List<Component> text = new ArrayList<>();
            text.add(Component.translatable(this.getDescriptionId() + ".break_line"));
            ILookOverlay.printGeneric(event, Component.translatable(block.getDescriptionId()), 0xffff00, 0x404000, text);
        }
    }

    public record Placement(BlockPos pos, Block block, Direction facing, ConveyorBlock.Shape shape) {

        /** The state to place, with the neighbour-derived pieces read from the given world at the given position. */
        public BlockState stateAt(BlockGetter level, BlockPos at) {
            if(this.block instanceof ConveyorBlock belt) return belt.stateFor(level, at, this.facing, this.shape);
            return ((ConveyorBaseBlock) this.block).stateFor(level, at, this.facing);
        }
    }

    /** @param result the number of belts when the route reaches the target, 0 when it needs more than the limit, -1 when blocked */
    public record Route(int result, List<Placement> placements) { }

    /**
     * ItemConveyorWand.java:362-460: walks greedily from the block outside the first clicked face towards the block outside
     * the second, turning when the next step gets no closer or is blocked; only the regular type goes up and down. Every
     * cell must be replaceable. The real build places exactly the cells this walk returns.
     */
    public static Route construct(Level routeWorld, ConveyorType type, Player player, BlockPos p1, Direction side1, BlockPos p2, Direction side2, int max) {

        List<Placement> placements = new ArrayList<>();
        Direction dir = side1;
        Direction targetDir = side2;

        // within a single block, placement works like a manual one with the player's facing
        if(p1.equals(p2) && side1 == side2 && dir.getAxis() == Direction.Axis.Y) {
            BlockPos at = p1.relative(dir);
            if(!routeWorld.getBlockState(at).canBeReplaced()) return new Route(-1, placements);
            placements.add(new Placement(at, getConveyorBlock(type), player.getDirection().getOpposite(), ConveyorBlock.Shape.STRAIGHT));
            return new Route(1, placements);
        }

        boolean hasVertical = hasSnakesAndLadders(type);

        BlockPos target = p2.relative(targetDir);
        BlockPos pos = p1.relative(dir);

        if(dir.getAxis() == Direction.Axis.Y) {
            dir = getTargetDirection(pos, p2, p2, null, false, hasVertical);
        }

        Block targetBlock = routeWorld.getBlockState(p2).getBlock();
        boolean isTargetHorizontal = targetDir.getAxis() != Direction.Axis.Y;
        boolean shouldTurnToTarget = isTargetHorizontal || targetBlock instanceof CraneBaseBlock || targetBlock == NtmBlocks.CONVEYOR_LIFT.get() || targetBlock == NtmBlocks.CONVEYOR_CHUTE.get();

        Direction horDir = dir.getAxis() == Direction.Axis.Y ? player.getDirection() : dir;

        // initial dropdown to floor level, if possible
        if(hasVertical && pos.getY() > target.getY()) {
            if(routeWorld.getBlockState(pos.below()).canBeReplaced()) {
                dir = Direction.DOWN;
            }
        }

        for(int loopDepth = 1; loopDepth <= max; loopDepth++) {
            if(!routeWorld.getBlockState(pos).canBeReplaced()) return new Route(-1, placements);

            Block block = getConveyorForDirection(type, dir);
            Direction facing = getConveyorFacingForDirection(block, dir, targetDir, horDir);
            ConveyorBlock.Shape shape = ConveyorBlock.Shape.STRAIGHT;

            BlockPos next = pos.relative(dir);

            // check if we should turn before continuing
            int fromDistance = pos.distManhattan(target);
            int toDistance = next.distManhattan(target);
            int finalDistance = next.distManhattan(p2);
            boolean notAtTarget = (shouldTurnToTarget ? finalDistance : fromDistance) > 0;
            boolean willBeObstructed = notAtTarget && !routeWorld.getBlockState(next).canBeReplaced();
            boolean shouldTurn = (toDistance >= fromDistance && notAtTarget) || willBeObstructed;

            if(shouldTurn) {
                Direction newDir = getTargetDirection(pos, shouldTurnToTarget ? p2 : target, target, dir, willBeObstructed, hasVertical);

                if(newDir == Direction.UP) {
                    block = NtmBlocks.CONVEYOR_LIFT.get();
                } else if(newDir == Direction.DOWN) {
                    block = NtmBlocks.CONVEYOR_CHUTE.get();
                } else if(dir.getAxis() != Direction.Axis.Y && dir.getClockWise() == newDir) {
                    shape = ConveyorBlock.Shape.RIGHT;
                } else if(dir.getAxis() != Direction.Axis.Y && dir.getCounterClockWise() == newDir) {
                    shape = ConveyorBlock.Shape.LEFT;
                }

                // a belt turned into a lift or chute keeps the input side worked out for the belt (:433-435)
                dir = newDir;
                if(dir.getAxis() != Direction.Axis.Y) horDir = dir;
            }

            placements.add(new Placement(pos, block, facing, shape));

            if(pos.equals(target)) return new Route(loopDepth, placements);

            pos = pos.relative(dir);
        }

        return new Route(0, placements);
    }

    /** ItemConveyorWand.java:474-478: a belt's input is behind it; a lift or chute faces the target side, or away from the heading. */
    private static Direction getConveyorFacingForDirection(Block block, Direction dir, Direction targetDir, Direction horDir) {
        if(block != NtmBlocks.CONVEYOR_CHUTE.get() && block != NtmBlocks.CONVEYOR_LIFT.get()) return dir.getOpposite();
        if(targetDir.getAxis() == Direction.Axis.Y) return horDir.getOpposite();
        return targetDir;
    }

    private static Block getConveyorForDirection(ConveyorType type, Direction dir) {
        if(dir == Direction.UP) return NtmBlocks.CONVEYOR_LIFT.get();
        if(dir == Direction.DOWN) return NtmBlocks.CONVEYOR_CHUTE.get();
        return getConveyorBlock(type);
    }

    /** ItemConveyorWand.java:486-499 */
    private static Direction getTargetDirection(BlockPos from, BlockPos to, BlockPos target, @Nullable Direction heading, boolean willBeObstructed, boolean hasVertical) {
        int x1 = from.getX(), y1 = from.getY(), z1 = from.getZ();
        int x2 = to.getX(), y2 = to.getY(), z2 = to.getZ();

        if(hasVertical && (y1 != y2 || y1 != target.getY()) && (willBeObstructed || (x1 == x2 && z1 == z2) || (x1 == target.getX() && z1 == target.getZ()))) {
            return y1 > y2 ? Direction.DOWN : Direction.UP;
        }

        if(Math.abs(x1 - x2) > Math.abs(z1 - z2)) {
            if(heading == Direction.EAST || heading == Direction.WEST) return z1 > z2 ? Direction.NORTH : Direction.SOUTH;
            return x1 > x2 ? Direction.WEST : Direction.EAST;
        } else {
            if(heading == Direction.NORTH || heading == Direction.SOUTH) return x1 > x2 ? Direction.WEST : Direction.EAST;
            return z1 > z2 ? Direction.NORTH : Direction.SOUTH;
        }
    }
}
