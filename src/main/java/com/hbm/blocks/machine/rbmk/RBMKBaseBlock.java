package com.hbm.blocks.machine.rbmk;

import api.hbm.block.IToolable;
import com.hbm.blockentity.machine.rbmk.RBMKBaseBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKDials;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.ILookOverlay;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.RBMKLidItem;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.util.StringRepresentable;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.EnumProperty;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import java.util.Arrays;
import java.util.List;
import java.util.Set;

/**
 * Original RBMKBase: one RBMK column, a core with {@link RBMKDials#getColumnHeight()} dummies stacked on it. The column has no
 * facing (the original forces DIR_NO_LID, RBMKBase.java:173-176) and keeps its lid in the core's {@link #LID} state instead of
 * the original's core metadata (:150-165).
 */
public abstract class RBMKBaseBlock extends DummyableBlock implements IToolable, ILookOverlay {

    public static final EnumProperty<LidType> LID = EnumProperty.create("lid", LidType.class);

    /** Original RBMKBase.dropLids (:37): meltdown() turns it off so melting columns never drop their lids. */
    public static boolean dropLids = true;

    // Original getCollisionBoundingBoxFromPool (:127-148): a lid raises the collision box of every block of the column by 0.25.
    private static final VoxelShape LID_SHAPE = Shapes.box(0, 0, 0, 1, 1.25, 1);

    public RBMKBaseBlock(Properties properties) {
        // Dynamic shape: the collision height depends on the core's lid, not on this state. A cached (full-block) shape would also
        // report no large collision shape, and entity collision skips the boundary cells of such blocks, ignoring the extra 0.25.
        super(properties.dynamicShape());
        this.registerDefaultState(this.defaultBlockState().setValue(LID, LidType.NONE));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        super.createBlockStateDefinition(builder);
        builder.add(LID);
    }

    // The body is a plain full cube in the original (isOpaqueCube, renderAsNormalBlock, :58-59); only the lid uses a renderer.
    @Override
    protected RenderShape getRenderShape(BlockState state) { return RenderShape.MODEL; }

    /** Decision 4 of GOAL24: the configured height is used for the placement check as well as for the fill (the original checks a fixed 3, :96-98). */
    @Override public int[] getDimensions() { return new int[] {RBMKDials.getColumnHeight(), 0, 0, 0, 0, 0}; }
    @Override public int getOffset() { return 0; }

    @Override
    protected Direction getDirModified(Direction dir) {
        return Direction.NORTH;
    }

    @Override
    protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        super.fillSpace(level, pos, dir, offset);
        this.makeExtra(level, pos.above(RBMKDials.getColumnHeight()));
    }

    /**
     * The lid of the column the given block belongs to, read from the core's state. Collision shapes are queried by the client and
     * the integrated server at the same time, so this follows the dummies down itself instead of using findCore's shared list.
     */
    public LidType getLid(BlockGetter level, BlockPos pos) {
        BlockPos.MutableBlockPos cursor = pos.mutable();
        for(int i = 0; i <= 16; i++) {
            BlockState state = level.getBlockState(cursor);
            if(state == null || state.getBlock() != this) return LidType.NONE;
            if(isCore(state)) return state.getValue(LID);
            cursor.move(getPointingDirection(state).getOpposite());
        }
        return LidType.NONE;
    }

    /**
     * Original hasOwnLid (:68-71): the control columns carry their own lid. Their lid is not removable, so the original's hasLid() is
     * always true for them and their collision box is always raised; they never get a lid state, which is why the shape asks this.
     */
    protected boolean hasOwnLid() {
        return false;
    }

    @Override
    protected VoxelShape getCollisionShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return this.hasOwnLid() || this.getLid(level, pos) != LidType.NONE ? LID_SHAPE : Shapes.block();
    }

    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hitResult) {
        // A held lid is placed by RBMKLidItem.useOn. Passive columns have no GUI; the slotted columns (RBMKRodBlock) override this and open theirs (original openInv, :105-125).
        if(stack.getItem() instanceof RBMKLidItem) return ItemInteractionResult.SKIP_DEFAULT_BLOCK_INTERACTION;
        return super.useItemOn(stack, state, level, pos, player, hand, hitResult);
    }

    /** Drops the item of the given lid at the column top, as the original breakBlock and onScrew do (:188, :222). */
    public static void dropLid(Level level, BlockPos core, LidType lid) {
        ItemStack stack = switch(lid) {
            case STANDARD -> new ItemStack(NtmItems.RBMK_LID.get());
            case GLASS -> new ItemStack(NtmItems.RBMK_LID_GLASS.get());
            case NONE -> ItemStack.EMPTY;
        };
        if(stack.isEmpty()) return;
        level.addFreshEntity(new ItemEntity(level, core.getX() + 0.5, core.getY() + 0.5 + RBMKDials.getColumnHeight(), core.getZ() + 0.5, stack));
    }

    /** Original breakBlock (:182-196): a removed core drops its lid unless a meltdown is running. A same-block state change (lid on or off) is no removal. */
    @Override
    public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean isMoving) {
        if(!level.isClientSide && dropLids && isCore(state) && !state.is(newState.getBlock())) {
            dropLid(level, pos, state.getValue(LID));
        }
        super.onRemove(state, level, pos, newState, isMoving);
    }

    /** Original onScrew (:198-239): a screwdriver takes the lid off and drops it. */
    @Override
    public boolean onScrew(Level level, Player player, BlockPos pos, Direction direction, ToolType tool) {

        if(tool != ToolType.SCREWDRIVER) return false;

        BlockPos core = this.findCore(level, pos);
        if(core == null) return false;
        if(!(level.getBlockEntity(core) instanceof RBMKBaseBlockEntity rbmk)) return false;
        if(!rbmk.hasLid() || !rbmk.isLidRemovable()) return false;

        if(!level.isClientSide) {
            BlockState coreState = level.getBlockState(core);
            dropLid(level, core, coreState.getValue(LID));
            level.setBlock(core, coreState.setValue(LID, LidType.NONE), 3);
            rbmk.onLidChanged();
        }

        return true;
    }

    /** Original TileEntityRBMKBase.diagnosticPrintHook (:313-376), the "Dump of Ordered Data Diagnostic" overlay. */
    @Override
    @OnlyIn(Dist.CLIENT)
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {

        BlockPos core = this.findCore(level, pos);
        if(core == null) return;
        if(!(level.getBlockEntity(core) instanceof RBMKBaseBlockEntity rbmk)) return;

        Minecraft mc = Minecraft.getInstance();
        if(mc.options.hideGui) return;

        CompoundTag flush = new CompoundTag();
        rbmk.getDiagData(flush);

        GuiGraphics graphics = event.getGuiGraphics();
        Font font = mc.font;

        int pX = mc.getWindow().getGuiScaledWidth() / 2 + 8;
        int pZ = mc.getWindow().getGuiScaledHeight() / 2;

        List<String> exceptions = List.of("x", "y", "z", "items", "id", "muffled");

        //Keep the title unlocalized is cool.
        String title = "Dump of Ordered Data Diagnostic (DODD)";
        graphics.drawString(font, title, pX + 1, pZ - 19, 0x006000, false);
        graphics.drawString(font, title, pX, pZ - 20, 0x00FF00, false);

        Component name = Component.translatable(this.getDescriptionId());
        graphics.drawString(font, name, pX + 1, pZ - 9, 0x606000, false);
        graphics.drawString(font, name, pX, pZ - 10, 0xffff00, false);

        Set<String> keys = flush.getAllKeys();
        String[] ents = keys.toArray(new String[0]);
        Arrays.sort(ents);

        for(String key : ents) {

            if(exceptions.contains(key)) continue;
            Tag tag = flush.get(key);
            String value = tag == null ? "" : tag.toString();
            //No...’d‘ doesn't refer to "day" and ‘s’ doesn't refer to "second". Meaningless.
            if(!value.isEmpty()) {
                char lastChar = value.charAt(value.length() - 1);
                if(lastChar == 'd' || lastChar == 's' || lastChar == 'b') {
                    value = value.substring(0, value.length() - 1);
                }
            }
            graphics.drawString(font, Component.translatable("tile.rbmk.dodd." + key).append(": " + value), pX, pZ, 0xFFFFFF, false);
            pZ += 10;
        }
    }

    /** Original NORTH / EAST / SOUTH core metadata (RBMKBase.java:150-159): no lid, concrete lid, lead glass lid. */
    public enum LidType implements StringRepresentable {
        NONE("none"),
        STANDARD("standard"),
        GLASS("glass");

        private final String name;

        LidType(String name) {
            this.name = name;
        }

        @Override
        public String getSerializedName() {
            return this.name;
        }
    }
}
