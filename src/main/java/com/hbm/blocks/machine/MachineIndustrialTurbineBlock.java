package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineIndustrialTurbineBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.ILookOverlay;
import com.hbm.blocks.ITooltipProvider;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.fluid.trait.FT_Coolable;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.util.BobMathUtil;
import com.hbm.util.SoundUtils;
import com.mojang.serialization.MapCodec;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item.TooltipContext;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.client.event.RenderGuiEvent.Pre;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class MachineIndustrialTurbineBlock extends DummyableBlock implements ITooltipProvider, ILookOverlay {

    public MachineIndustrialTurbineBlock(Properties properties) {
        super(properties);
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        DummyBlockType type = state.getValue(TYPE);
        return switch(type) {
            case CORE -> new MachineIndustrialTurbineBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state).fluid().power();
            default -> null;
        };
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    public static final MapCodec<MachineIndustrialTurbineBlock> CODEC = simpleCodec(MachineIndustrialTurbineBlock::new);
    @Override public MapCodec<MachineIndustrialTurbineBlock> codec() { return CODEC; }

    @Override public int[] getDimensions() { return new int[] { 2, 0, 3, 3, 1, 1 }; }
    @Override public int getOffset() { return 3; }

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult) {

        if(!player.isShiftKeyDown()) {
            BlockPos corePos = this.findCore(level, pos);
            // The original consumes the click when the core is missing.
            if(corePos == null) return InteractionResult.sidedSuccess(level.isClientSide);

            BlockEntity blockEntity = level.getBlockEntity(corePos);
            if(blockEntity instanceof MachineIndustrialTurbineBlockEntity be) {

                Direction dir = level.getBlockState(corePos).getValue(FACING);
                BlockPos leverPos = corePos.offset(dir.getStepX() * 3, 1, dir.getStepZ() * 3);

                if(pos.equals(leverPos)) {

                    if(!level.isClientSide) {
                        if(!be.operational) {
                            SoundUtils.playAtVec3(level, Vec3.atCenterOf(pos), NtmSoundEvents.TURBINE_LEVER.get(), SoundSource.BLOCKS, 1.5F, 1F);
                            be.onLeverPull();
                        } else {
                            player.sendSystemMessage(Component.translatable("machine_industrial_turbine.compressor_locked").withStyle(ChatFormatting.RED));
                        }
                    }

                    return InteractionResult.sidedSuccess(level.isClientSide);
                }
            }
        }

        return InteractionResult.PASS;
    }

    @Override
    protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        super.fillSpace(level, pos, dir, offset);

        // The original's rotated port table (getAllPorts), relative to the core like the original tile entity's port
        // definitions: four fluid ports on the sides, two on top and the power port at the back. The original adds the
        // table to the placed block (core + 3 * dir) after rotatePorts has shifted it by -3 * dir, so the cells are the same.
        BlockPos core = pos.relative(dir, offset);
        Direction rot = dir.getClockWise();

        this.makeExtra(level, core.relative(dir, 3).relative(rot));
        this.makeExtra(level, core.relative(dir, 3).relative(rot.getOpposite()));
        this.makeExtra(level, core.relative(dir.getOpposite()).relative(rot));
        this.makeExtra(level, core.relative(dir.getOpposite()).relative(rot.getOpposite()));
        this.makeExtra(level, core.relative(dir, 3).above(2));
        this.makeExtra(level, core.relative(dir.getOpposite()).above(2));
        this.makeExtra(level, core.relative(dir.getOpposite(), 3).above());
    }

    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> components, TooltipFlag flag) {
        this.addStandardInfo(components);
    }

    private static final String[] blocks = new String[] {"▖ ", "▘ ", " ▘", " ▖"}; // right hand side quarter blocks break the renderer so we cheat a little

    @Override
    public void printHook(Pre event, Level level, BlockPos pos) {
        BlockPos corePos = this.findCore(level, pos);
        if(corePos == null) return;

        BlockEntity blockEntity = level.getBlockEntity(corePos);
        if(!(blockEntity instanceof MachineIndustrialTurbineBlockEntity turbine)) return;

        List<Component> text = new ArrayList<>();

        FluidTank tankInput = turbine.tanks[0];
        FluidTank tankOutput = turbine.tanks[1];

        FluidType inputType = tankInput.getTankType();
        FluidType outputType = Fluids.NONE;

        if(inputType.hasTrait(FT_Coolable.class)) outputType = inputType.getTrait(FT_Coolable.class).coolsTo;

        // Clamped so a spin outside 0..1 cannot bleed into the other colour channels; identical to the original within that range.
        int red = Math.max(0, Math.min(0xFF, (int) (0xFF - 0xFF * turbine.spin)));
        int green = Math.max(0, Math.min(0xFF, (int) (0xFF * turbine.spin)));
        int color = red << 16 | green << 8;
        int time = (int) ((level.getGameTime() / 4) % 4);

        // Siblings of an unstyled root, so only the arrows take the arrow colour, as the original's RESET does.
        text.add(Component.empty().append(Component.literal("-> ").withStyle(ChatFormatting.GREEN))
                .append(inputType.getName()).append(": " + String.format(Locale.US, "%,d", tankInput.getFill()) + "/" + String.format(Locale.US, "%,d", tankInput.getMaxFill()) + "mB"));
        text.add(Component.empty().append(Component.literal("<- ").withStyle(ChatFormatting.RED))
                .append(outputType.getName()).append(": " + String.format(Locale.US, "%,d", tankOutput.getFill()) + "/" + String.format(Locale.US, "%,d", tankOutput.getMaxFill()) + "mB"));
        text.add(Component.empty().append(Component.literal("<- ").withStyle(ChatFormatting.RED))
                .append(Component.literal(BobMathUtil.getShortNumber(turbine.powerBuffer) + "HE (").withStyle(ChatFormatting.WHITE))
                .append(Component.literal(blocks[turbine.powerBuffer <= 0 ? 0 : time] + Math.round(turbine.spin * 100) + "%").withColor(color))
                .append(Component.literal(")").withStyle(ChatFormatting.WHITE)));

        ILookOverlay.printGeneric(event, this.getName(), 0xffff00, 0x404000, text);
    }
}
