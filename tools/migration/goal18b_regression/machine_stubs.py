"""Goal18B machine world: the Goal18A machine world unchanged. The production crystallizer, centrifuge, turbofan, PowerNetMK2 and
UniNodespace are already compiled there as production; the crystallizer and centrifuge tables stay declared services whose 18B rows
are set by the fixture (mirroring the production defaults the verifier resolves). No stand-in tweak is needed for the 18B fixture."""
from goal18a_regression.machine_stubs import machine_stubs as base_stubs, MACHINE_SOURCES, EXTRACTED

def machine_stubs(source, extras, tags, jar):
    return base_stubs(source, extras, tags, jar)
