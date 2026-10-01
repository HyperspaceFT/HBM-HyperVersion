package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineStirlingBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.ILookOverlay;
import com.hbm.blocks.ITooltipProvider;
import com.hbm.inventory.MetaHelper;
import com.hbm.items.NtmItems;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.util.BobMathUtil;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import javax.annotation.Nullable;
import java.util.ArrayList;
import java.util.List;

public class MachineStirlingBlock extends DummyableBlock implements ILookOverlay, ITooltipProvider {

    public MachineStirlingBlock(Properties properties) {
        super(properties);
    }

    public static final MapCodec<MachineStirlingBlock> CODEC = simpleCodec(MachineStirlingBlock::new);
    @Override public MapCodec<MachineStirlingBlock> codec() { return CODEC; }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        DummyBlockType type = state.getValue(TYPE);
        return switch(type) {
            case CORE -> new MachineStirlingBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state).power();
            default -> null;
        };
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override public int[] getDimensions() { return new int[] { 1, 0, 1, 1, 1, 1 }; }
    @Override public int getOffset() { return 1; }

    @Override
    protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        super.fillSpace(level, pos, dir, offset);

        BlockPos core = pos.relative(dir, offset);
        this.makeExtra(level, core.east());
        this.makeExtra(level, core.west());
        this.makeExtra(level, core.south());
        this.makeExtra(level, core.north());
    }

    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hitResult) {
        if(player.isShiftKeyDown()) return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
        // Deviation from the original, which swallowed every right click: only the gear is handled here.
        if(!stack.is(NtmItems.GEAR_LARGE.get())) return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
        if(level.isClientSide) return ItemInteractionResult.SUCCESS;

        BlockPos corePos = this.findCore(level, pos);
        if(corePos == null) return ItemInteractionResult.FAIL;

        if(level.getBlockEntity(corePos) instanceof MachineStirlingBlockEntity stirling && stirling.tryInstallGear(stack)) {
            level.playSound(null, pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5, NtmSoundEvents.UPGRADE_PLUG.get(), SoundSource.BLOCKS, 1.5F, 0.75F);
            return ItemInteractionResult.SUCCESS;
        }

        return ItemInteractionResult.FAIL;
    }

    @Override
    public void setPlacedBy(Level level, BlockPos pos, BlockState state, @Nullable LivingEntity placer, ItemStack stack) {
        super.setPlacedBy(level, pos, state, placer, stack);

        // Meta 1 is the gearless engine item; the core position mirrors DummyableBlock.setPlacedBy.
        // After a failed placement the clicked position is air again, so the neighbouring engine (whose core would be
        // at the same position) keeps its gear; the original stripped it.
        if(!level.isClientSide && MetaHelper.getMeta(stack) == 1 && level.getBlockState(pos).is(this)) {
            BlockPos corePos = pos.above(this.getHeightOffset()).relative(this.getDirModified(state.getValue(FACING)), -this.getOffset());

            if(level.getBlockEntity(corePos) instanceof MachineStirlingBlockEntity stirling) {
                stirling.hasCog = false;
                stirling.setChanged();
            }
        }
    }

    @Override
    protected List<ItemStack> getDrops(BlockState state, LootParams.Builder params) {
        List<ItemStack> drops = super.getDrops(state, params);
        BlockEntity be = params.getOptionalParameter(LootContextParams.BLOCK_ENTITY);

        // Player breaks pass the core block entity (DummyableBlock.playerWillDestroy). Explosions pass whatever sits at
        // the exploded part, so resolve the core from the origin like the original MachineStirling.getDrops did.
        if(!(be instanceof MachineStirlingBlockEntity)) {
            Vec3 origin = params.getOptionalParameter(LootContextParams.ORIGIN);
            ServerLevel level = params.getLevel();
            BlockPos corePos = origin == null ? null : this.findCore(level, BlockPos.containing(origin));
            if(corePos != null) be = level.getBlockEntity(corePos);
        }

        // Only the gearless form is marked; a plain stack (no META component) is the engine with its gear.
        if(be instanceof MachineStirlingBlockEntity stirling) {
            int meta = stirling.getDropMeta();
            if(meta != 0) drops.forEach(drop -> MetaHelper.setMeta(drop, meta));
        }

        return drops;
    }

    @Override
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        BlockPos corePos = this.findCore(level, pos);
        if(corePos == null) return;

        BlockEntity te = level.getBlockEntity(corePos);
        if(!(te instanceof MachineStirlingBlockEntity stirling)) return;

        List<Component> text = new ArrayList<>();
        text.add(Component.literal(String.format("%,d", stirling.heat) + " TU/t"));
        text.add(Component.literal(String.format("%,d", stirling.hasCog ? stirling.powerBuffer : 0) + " HE/t"));

        int maxHeat = MachineStirlingBlockEntity.MAX_HEAT;
        double percent = (double) stirling.heat / (double) maxHeat;
        int color = ((int) (0xFF - 0xFF * percent)) << 16 | ((int)(0xFF * percent) << 8);

        if(percent > 1D)
            color = 0xff0000;

        text.add(Component.literal(((stirling.heat * 1000 / maxHeat) / 10D) + "%").withColor(color));

        if(stirling.heat > maxHeat) {
            text.add(Component.translatable("machine_stirling.overlay.overspeed").withColor(BobMathUtil.getBlink() ? 0xff0000 : 0xffff00));
        }

        if(!stirling.hasCog) {
            text.add(Component.translatable("machine_stirling.overlay.gear_missing").withColor(0xff0000));
        }

        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xffff00, 0x404000, text);
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {
        this.addStandardInfo(components);
    }
}
