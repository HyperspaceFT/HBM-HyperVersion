"""Reuse Goal 12B stand-ins; fill its previously unused clipboard method from production."""

from goal10b_regression.stubs import method_body
from goal12b_regression.stubs import build_stubs as goal12b_stubs


def build_stubs(source, extra_sources, vanilla_tags_source, sources_jar):
    stubs = goal12b_stubs(source, extra_sources, vanilla_tags_source, sources_jar)
    name = "com/hbm/blockentity/IFluidCopiable.java"
    body = method_body((source / name).read_text(encoding="utf-8"),
                       "default void pasteSettings(", name)
    anchor = "default void pasteSettings(CompoundTag t,int i,Level l,Player p,BlockPos pos){}"
    if stubs[name].count(anchor) != 1:
        raise SystemExit("Clipboard fixture anchor changed")
    stubs[name] = stubs[name].replace(anchor, body).replace(
        "import com.hbm.inventory.fluid.tank.FluidTank;",
        "import com.hbm.inventory.fluid.tank.FluidTank;import com.hbm.inventory.fluid.Fluids;")
    return stubs
