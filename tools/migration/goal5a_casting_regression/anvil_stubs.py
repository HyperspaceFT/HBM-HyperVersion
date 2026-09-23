"""Reuse the established anvil fixture services with real cast-plate identity matching."""

from goal3a_regression.anvil_stubs import make_anvil_stubs
from verify_goal2 import STUBS


def build_anvil_stubs(source):
    stubs = {name: STUBS[name] for name in (
        "net/minecraft/core/NonNullList.java", "net/minecraft/world/InteractionHand.java",
        "net/minecraft/world/entity/LivingEntity.java", "net/minecraft/network/RegistryFriendlyByteBuf.java",
    )}
    stubs.update(make_anvil_stubs(source))
    stubs["com/hbm/inventory/RecipesCommon.java"] = stubs["com/hbm/inventory/RecipesCommon.java"].replace(
        'public static class TagStack extends AStack {public TagStack(Object tag,int n){super(new Item("tag:"+tag),n);}}',
        'public static class TagStack extends AStack {private final Object tag;'
        'public TagStack(Object tag,int n){super(new Item("tag:"+tag),n);this.tag=tag;}'
        'public boolean matchesRecipe(ItemStack s,boolean ignore){return '
        '((tag==NtmTags.Items.PLATES_STEEL&&s.is(com.hbm.items.NtmItems.PLATE_STEEL.get()))'
        '||(tag==net.minecraft.tags.ItemTags.LOGS&&!s.isEmpty()&&s.getItem().id.contains("log")))'
        '&&(ignore||s.getCount()>=stacksize);}'
        'public AStack copy(){return new TagStack(tag,stacksize);}}'
    )
    stubs["com/hbm/items/NtmItems.java"] = stubs["com/hbm/items/NtmItems.java"].replace(
        'new ComparableStack(new Item("cast_plate_"+type),count)',
        'new ComparableStack(CAST_PLATE.get(),count,type.ordinal())'
    )
    return stubs
