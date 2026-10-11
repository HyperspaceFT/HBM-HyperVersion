"""Goal17A service stand-ins extend unchanged Goal16A infrastructure."""
from goal16a_regression.acquisition_stubs import build_stubs as previous

def build_stubs(source):
    stubs = previous(source)
    key = "com/hbm/items/NtmItems.java"
    anchor = 'MOLD_INGOT=new Ref(new Item("hbmsntm:mold_ingot"))'
    assert stubs[key].count(anchor) == 1
    extra = ','.join(name + '=new Ref(new Item("hbmsntm:' + name.lower() + '"))' for name in ("MOLD_BLADE", "BLADE_TITANIUM", "BLADE_TUNGSTEN"))
    stubs[key] = stubs[key].replace(anchor, anchor + ',' + extra)
    key = "net/minecraft/nbt/CompoundTag.java"
    anchor = "public void putInt(String k,int v)"
    assert stubs[key].count(anchor) == 1
    stubs[key] = stubs[key].replace(anchor, "public void remove(String k){m.remove(k);}" + anchor)
    return stubs
