package com.hbm.items.machine;

import com.hbm.inventory.MetaHelper;
import com.hbm.items.ICustomItemModelRegister;
import com.hbm.items.IMetaItem;
import com.hbm.items.NuclearWasteItem;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.main.NuclearTechMod;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.neoforged.neoforge.client.model.generators.ItemModelBuilder;
import net.neoforged.neoforge.client.model.generators.ItemModelProvider;
import net.neoforged.neoforge.client.model.generators.ModelFile;

import java.util.List;

/**
 * Port of the original com.hbm.items.machine.ItemRBMKPellet (HBM's Nuclear Tech). The original damage value is the META component:
 * META % 5 is the depletion tier and META 5-9 the same tiers with high xenon poison. The hard-coded full name became the language key
 * {@link #getFullNameKey}, which the rod made from this pellet shows too.
 */
public class RBMKPelletItem extends NuclearWasteItem implements IMetaItem, ICustomItemModelRegister {

    protected boolean hasXenon = true;

    public RBMKPelletItem(Properties properties) {
        super(properties.component(NtmDataComponents.META.get(), 0));
    }

    public RBMKPelletItem disableXenon() {
        this.hasXenon = false;
        return this;
    }

    public boolean isXenonEnabled() {
        return hasXenon;
    }

    public String getFullNameKey() {
        return getDescriptionId() + ".fullName";
    }

    @Override
    public void getSubItems(Item item, List<ItemStack> stacks) {
        for(int i = 0; i < (this.hasXenon ? 10 : 5); ++i) {
            stacks.add(MetaHelper.newStack(item, 1, i));
        }
    }

    /**
     * Original render passes (:53-111): the pellet texture, the enrichment overlay of rectify(META) % 5 and, from rectify(META) 5 on, the
     * xenon overlay. The item_meta predicate (NuclearTechModClient) returns rectify(META). Pellets without xenon get no xenon models and their
     * predicate returns rectify(META) % 5, so a command-made META 5-9 stack of one of them shows that look (the original drew its
     * unregistered xenon icon there).
     */
    @Override
    public void registerItemModel(ItemModelProvider provider, ResourceLocation modelLocation) {
        String namespace = modelLocation.getNamespace();
        ResourceLocation texture = ResourceLocation.fromNamespaceAndPath(namespace, "item/" + modelLocation.getPath());

        ItemModelBuilder builder = provider.getBuilder(modelLocation.toString())
                .parent(new ModelFile.UncheckedModelFile("item/generated"))
                .texture("layer0", texture)
                .texture("layer1", overlay(namespace, "rbmk_pellet_overlay_e0"));

        for(int i = 0; i < (this.hasXenon ? 10 : 5); i++) {
            ItemModelBuilder model = provider.getBuilder(modelLocation.getPath() + "_" + i)
                    .parent(new ModelFile.UncheckedModelFile("item/generated"))
                    .texture("layer0", texture)
                    .texture("layer1", overlay(namespace, "rbmk_pellet_overlay_e" + (i % 5)));

            if(i >= 5) model.texture("layer2", overlay(namespace, "rbmk_pellet_overlay_xenon"));

            builder.override()
                    .predicate(NuclearTechMod.withDefaultNamespace("item_meta"), i)
                    .model(model)
                    .end();
        }
    }

    private static ResourceLocation overlay(String namespace, String name) {
        return ResourceLocation.fromNamespaceAndPath(namespace, "item/" + name);
    }

    // Original addInformation (:79-98); the hard-coded English lines became desc.item.rbmkPellet.* keys.
    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltipComponents, TooltipFlag tooltipFlag) {
        super.appendHoverText(stack, context, tooltipComponents, tooltipFlag);

        tooltipComponents.add(Component.translatable(getFullNameKey()).withStyle(ChatFormatting.ITALIC));
        tooltipComponents.add(Component.translatable("desc.item.rbmkPellet.recycling").withStyle(ChatFormatting.DARK_GRAY, ChatFormatting.ITALIC));

        int meta = rectify(MetaHelper.getMeta(stack));

        switch(meta % 5) {
            case 0: tooltipComponents.add(Component.translatable("desc.item.rbmkPellet.brandNew").withStyle(ChatFormatting.GOLD)); break;
            case 1: tooltipComponents.add(Component.translatable("desc.item.rbmkPellet.barelyDepleted").withStyle(ChatFormatting.YELLOW)); break;
            case 2: tooltipComponents.add(Component.translatable("desc.item.rbmkPellet.moderatelyDepleted").withStyle(ChatFormatting.GREEN)); break;
            case 3: tooltipComponents.add(Component.translatable("desc.item.rbmkPellet.highlyDepleted").withStyle(ChatFormatting.DARK_GREEN)); break;
            case 4: tooltipComponents.add(Component.translatable("desc.item.rbmkPellet.fullyDepleted").withStyle(ChatFormatting.DARK_GRAY)); break;
        }

        // A static META test as in the original, so it also shows on a xenon-disabled pellet with META 5-9.
        if(hasXenon(meta))
            tooltipComponents.add(Component.translatable("desc.item.rbmkPellet.highXenon").withStyle(ChatFormatting.DARK_PURPLE));
    }

    public static boolean hasXenon(int meta) {
        return rectify(meta) >= 5;
    }

    public static int rectify(int meta) {
        return Math.abs(meta) % 10;
    }
}
